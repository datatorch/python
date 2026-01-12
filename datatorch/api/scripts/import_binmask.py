import os
import glob
import logging
import pathlib
import numpy as np
import tqdm

from typing import List, Dict, Optional, Tuple
from .utils.simplify import simplify_points

from .. import ApiClient, File, Where, Project
from ...utils.converters import (
    binmask2cocopoly,
    points_to_segmentation,
    segmentation_to_points,
    simplify_segmentation,
)

try:
    import cv2
except ImportError:
    raise ImportError(
        "OpenCV is required for binary mask import. Install it with:\n"
        "\tpip install opencv-python"
    )

_LOGGER = logging.getLogger(__name__)


def mask_to_polygons(
    mask: np.ndarray,
    simplify_tolerance: float = 1.0,
    min_area: float = 100.0,
) -> List[List[List[float]]]:
    """
    Convert a binary mask to polygon contours using OpenCV.

    Args:
        mask: Binary mask image (numpy array)
        simplify_tolerance: Tolerance for polygon simplification (0 to disable)
        min_area: Minimum polygon area to include

    Returns:
        List of polygons in [[[x1,y1], [x2,y2], ...]] format
    """
    # Ensure mask is binary uint8
    if mask.max() > 1:
        mask = (mask > 127).astype(np.uint8)
    else:
        mask = mask.astype(np.uint8)

    # Use the existing converter to get COCO polygon format [[x1,y1,x2,y2,...]]
    try:
        coco_segmentation = binmask2cocopoly(mask)
    except ValueError:
        # No valid polygons found
        return []

    # Convert from COCO format to points format and filter by area
    polygons = []
    for seg in coco_segmentation:
        # seg is [x1,y1,x2,y2,...], convert to [[x1,y1], [x2,y2], ...]
        points = np.reshape(seg, (-1, 2)).tolist()

        if len(points) < 3:
            continue

        # Calculate area using shoelace formula
        poly_array = np.array(points)
        x = poly_array[:, 0]
        y = poly_array[:, 1]
        area = 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

        if area < min_area:
            continue

        polygons.append(points)

    if simplify_tolerance > 0 and len(polygons) > 0:
        # Simplify polygons
        simplified = [
            simplify_points(polygon, tolerance=simplify_tolerance, highestQuality=False)
            for polygon in polygons
        ]
        # Filter out polygons that became too small after simplification
        polygons = [p for p in simplified if len(p) >= 3]

    return polygons


def find_mask_files(
    mask_folder: str,
    extensions: List[str] = None,
) -> Dict[str, str]:
    """
    Find all mask files in a folder.

    Args:
        mask_folder: Path to folder containing mask images
        extensions: List of image extensions to look for

    Returns:
        Dictionary mapping base filename (without extension) to full path
    """
    if extensions is None:
        extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"]

    mask_files = {}
    for ext in extensions:
        for filepath in glob.glob(os.path.join(mask_folder, f"*{ext}")):
            basename = os.path.splitext(os.path.basename(filepath))[0]
            mask_files[basename] = filepath
        # Also check uppercase extensions
        for filepath in glob.glob(os.path.join(mask_folder, f"*{ext.upper()}")):
            basename = os.path.splitext(os.path.basename(filepath))[0]
            mask_files[basename] = filepath

    return mask_files


def parse_mask_filename(
    mask_filename: str,
    suffix: str = "_mask",
    label_name: str = None,
) -> Tuple[str, Optional[str]]:
    """
    Parse mask filename to extract original image name and optional label.

    Supports formats:
        - image_mask.png -> (image, None)
        - image_label_mask.png -> (image, label)
        - image.png -> (image, None)

    Args:
        mask_filename: Base filename of the mask (without extension)
        suffix: Suffix to strip from mask filename
        label_name: If provided, don't try to detect label from filename

    Returns:
        Tuple of (image_name, label_name or None)
    """
    # Strip suffix if it's not empty and the filename ends with it
    if suffix and mask_filename.endswith(suffix):
        mask_filename = mask_filename[: -len(suffix)]

    # If a label is already provided, don't try to detect from filename
    # Just return the full filename as the image name
    if label_name is not None:
        return mask_filename, None

    # Check if there's a label in the filename (format: imagename_labelname)
    # This is a simple heuristic - can be customized based on naming convention
    parts = mask_filename.rsplit("_", 1)
    if len(parts) == 2:
        # Could be image_label format
        return parts[0], parts[1]

    return mask_filename, None


_CREATE_ANNOTATIONS = """
    mutation CreateAnnotations($annotations: [CreateAnnotationInput!]!) {
        createAnnotations(annotations: $annotations)
    }
"""


def import_binmask(
    mask_folder: str,
    project_string: str,
    label_name: str = None,
    image_base_path: str = None,
    mask_suffix: str = "_mask",
    simplify_tolerance: float = 1.0,
    min_area: float = 100.0,
    file_extensions: List[str] = None,
    invert_mask: bool = False,
    skip_annotated: bool = False,
    api: ApiClient = None,
):
    """
    Import binary masks from a folder into DataTorch as polygon annotations.

    Images must already be uploaded and imported into DataTorch before running this.
    Use `datatorch upload folder` to upload images first.

    Args:
        mask_folder: Path to folder containing binary mask images
        project_string: DataTorch project identifier (e.g., "username/project" or UUID)
        label_name: Name of the label to assign to all annotations (required if masks don't have labels in filename)
        image_base_path: Base path for matching files in DataTorch (optional)
        mask_suffix: Suffix to strip from mask filenames (default: "_mask")
        simplify_tolerance: Tolerance for polygon simplification (0 to disable)
        min_area: Minimum polygon area to include as annotation
        file_extensions: List of image extensions to look for
        invert_mask: If True, invert the binary mask before processing
        skip_annotated: If True, skip files that already have annotations
        api: DataTorch API client (optional, will create one if not provided)
    """
    if not os.path.isdir(mask_folder):
        raise ValueError(f"Provided path '{mask_folder}' is not a directory.")

    # Get DataTorch project information
    _LOGGER.debug("Connecting to DataTorch API.")
    if api is None:
        api = ApiClient()

    _LOGGER.debug("Loading Project Information.")
    project: Project = api.project(project_string)

    labels = project.labels()
    _LOGGER.debug("Project ID: %s", project.id)
    names_mapping = dict(((label.name, label) for label in labels))

    # Check if project has any labels
    if len(names_mapping) == 0:
        raise ValueError(
            f"No labels found in project. "
            f"Please create at least one label in DataTorch first."
        )

    # Validate label if provided
    if label_name is not None and label_name not in names_mapping:
        available = list(names_mapping.keys())
        raise ValueError(
            f"Label '{label_name}' not found in project. "
            f"Available labels: {available}. "
            f"Please create the label in DataTorch first."
        )

    # Find all mask files
    mask_files = find_mask_files(mask_folder, file_extensions)

    if len(mask_files) == 0:
        _LOGGER.warning(f"No mask files found in '{mask_folder}'")
        return

    _LOGGER.info(f"Found {len(mask_files)} mask files to process.")

    # Process each mask file
    for mask_basename, mask_path in tqdm.tqdm(
        mask_files.items(), unit="mask", disable=None
    ):
        # Parse mask filename to get image name and optional label
        image_name, detected_label = parse_mask_filename(
            mask_basename, mask_suffix, label_name
        )

        # Determine which label to use
        current_label_name = label_name or detected_label
        if current_label_name is None:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.error(
                    f"[{mask_basename}] No label specified and couldn't detect from filename. "
                    "Use --label option or name files as 'imagename_labelname_mask.ext'"
                )
            continue

        label = names_mapping.get(current_label_name)
        if label is None:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.error(
                    f"[{mask_basename}] Label '{current_label_name}' not found in project."
                )
            continue

        # Try to find matching file in DataTorch
        # Try with common image extensions
        search_names = [
            image_name,
            f"{image_name}.png",
            f"{image_name}.jpg",
            f"{image_name}.jpeg",
            f"{image_name}.tif",
            f"{image_name}.tiff",
        ]

        dt_file = None
        multiple_found = False
        for search_name in search_names:
            if image_base_path is None:
                file_filter = Where(name=search_name)
            else:
                file_filter = Where(
                    path=str(
                        pathlib.PurePosixPath(image_base_path.strip("/")).joinpath(
                            search_name
                        )
                    )
                )

            dt_files = project.files(file_filter, limit=2)

            if len(dt_files) == 1:
                dt_file = dt_files[0]
                break
            elif len(dt_files) > 1:
                with tqdm.tqdm.external_write_mode():
                    _LOGGER.error(
                        f"[{mask_basename}] Multiple files found matching '{search_name}', skipping"
                    )
                multiple_found = True
                break

        # If multiple files found, skip this mask
        if multiple_found:
            continue

        # If no file found, skip with helpful error message
        if dt_file is None:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.error(
                    f"[{mask_basename}] No matching file found for '{image_name}'. "
                    f"Make sure images are uploaded first using 'datatorch upload folder'."
                )
            continue

        with tqdm.tqdm.external_write_mode():
            _LOGGER.info(f"[{mask_basename}] Matched to file: {dt_file.name}")

        # Skip completed files
        if dt_file.status == "COMPLETED":
            with tqdm.tqdm.external_write_mode():
                _LOGGER.warning(
                    f"[{mask_basename}] File is already marked as 'COMPLETED', skipping"
                )
            continue

        # Skip files that already have annotations if flag is set
        if skip_annotated and hasattr(dt_file, "annotations") and dt_file.annotations:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.info(
                    f"[{mask_basename}] File already has {len(dt_file.annotations)} annotation(s), skipping"
                )
            continue

        # Read the mask using OpenCV
        try:
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise ValueError(f"Could not read image file: {mask_path}")
        except Exception as e:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.error(f"[{mask_basename}] Failed to read mask file: {e}")
            continue

        if invert_mask:
            mask = 255 - mask

        # Convert mask to polygons
        polygons = mask_to_polygons(
            mask,
            simplify_tolerance=simplify_tolerance,
            min_area=min_area,
        )

        if len(polygons) == 0:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.warning(f"[{mask_basename}] No valid polygons found in mask")
            continue

        with tqdm.tqdm.external_write_mode():
            _LOGGER.debug(f"[{mask_basename}] Found {len(polygons)} polygons")

        # Create annotation for each polygon
        # DataTorch expects all polygons as a single annotation with multiple paths
        annotation = {
            "labelId": label.id,
            "fileId": dt_file.id,
            "sources": [
                {
                    "type": "PaperSegmentations",
                    "data": {"pathData": polygons},
                }
            ],
        }

        # Upload annotation
        api.execute(_CREATE_ANNOTATIONS, params={"annotations": [annotation]})

        with tqdm.tqdm.external_write_mode():
            _LOGGER.info(
                f"[{mask_basename}] Successfully uploaded annotation with {len(polygons)} polygon(s)"
            )

    _LOGGER.info("Binary mask import complete.")


def import_binmask_multi_label(
    mask_folder: str,
    project_string: str,
    label_mapping: Dict[int, str],
    image_base_path: str = None,
    mask_suffix: str = "_mask",
    simplify_tolerance: float = 1.0,
    min_area: float = 100.0,
    file_extensions: List[str] = None,
    api: ApiClient = None,
):
    """
    Import multi-class segmentation masks where each pixel value corresponds to a class.

    Images must already be uploaded and imported into DataTorch before running this.
    Use `datatorch upload folder` to upload images first.

    Args:
        mask_folder: Path to folder containing mask images
        project_string: DataTorch project identifier (e.g., "username/project" or UUID)
        label_mapping: Dictionary mapping pixel values to label names (e.g., {1: "car", 2: "person"})
        image_base_path: Base path for matching files in DataTorch (optional)
        mask_suffix: Suffix to strip from mask filenames (default: "_mask")
        simplify_tolerance: Tolerance for polygon simplification (0 to disable)
        min_area: Minimum polygon area to include as annotation
        file_extensions: List of image extensions to look for
        api: DataTorch API client (optional, will create one if not provided)
    """
    if not os.path.isdir(mask_folder):
        raise ValueError(f"Provided path '{mask_folder}' is not a directory.")

    # Get DataTorch project information
    _LOGGER.debug("Connecting to DataTorch API.")
    if api is None:
        api = ApiClient()

    _LOGGER.debug("Loading Project Information.")
    project: Project = api.project(project_string)

    labels = project.labels()
    _LOGGER.debug("Project ID: %s", project.id)
    names_mapping = dict(((label.name, label) for label in labels))

    # Validate all labels in mapping exist
    for pixel_value, label_name in label_mapping.items():
        if label_name not in names_mapping:
            raise ValueError(
                f"Label '{label_name}' (pixel value {pixel_value}) not found in project. "
                f"Available labels: {list(names_mapping.keys())}"
            )

    # Find all mask files
    mask_files = find_mask_files(mask_folder, file_extensions)

    if len(mask_files) == 0:
        _LOGGER.warning(f"No mask files found in '{mask_folder}'")
        return

    _LOGGER.info(f"Found {len(mask_files)} mask files to process.")

    # Process each mask file
    for mask_basename, mask_path in tqdm.tqdm(
        mask_files.items(), unit="mask", disable=None
    ):
        # Parse mask filename to get image name
        image_name, _ = parse_mask_filename(mask_basename, mask_suffix)

        # Try to find matching file in DataTorch
        search_names = [
            image_name,
            f"{image_name}.png",
            f"{image_name}.jpg",
            f"{image_name}.jpeg",
            f"{image_name}.tif",
            f"{image_name}.tiff",
        ]

        dt_file = None
        for search_name in search_names:
            if image_base_path is None:
                file_filter = Where(name=search_name)
            else:
                file_filter = Where(
                    path=str(
                        pathlib.PurePosixPath(image_base_path.strip("/")).joinpath(
                            search_name
                        )
                    )
                )

            dt_files = project.files(file_filter, limit=2)

            if len(dt_files) == 1:
                dt_file = dt_files[0]
                break
            elif len(dt_files) > 1:
                with tqdm.tqdm.external_write_mode():
                    _LOGGER.error(
                        f"[{mask_basename}] Multiple files found matching '{search_name}', skipping"
                    )
                break

        if dt_file is None:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.error(
                    f"[{mask_basename}] No matching file found for '{image_name}'. "
                    f"Make sure images are uploaded first using 'datatorch upload folder'."
                )
            continue

        with tqdm.tqdm.external_write_mode():
            _LOGGER.info(f"[{mask_basename}] Matched to file: {dt_file.name}")

        # Skip completed files
        if dt_file.status == "COMPLETED":
            with tqdm.tqdm.external_write_mode():
                _LOGGER.warning(
                    f"[{mask_basename}] File is already marked as 'COMPLETED', skipping"
                )
            continue

        # Read the mask using OpenCV
        try:
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise ValueError(f"Could not read image file: {mask_path}")
        except Exception as e:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.error(f"[{mask_basename}] Failed to read mask file: {e}")
            continue

        # Process each class in the mask
        new_annotations = []
        for pixel_value, label_name in label_mapping.items():
            # Create binary mask for this class
            class_mask = (mask == pixel_value).astype(np.uint8) * 255

            # Convert to polygons
            polygons = mask_to_polygons(
                class_mask,
                simplify_tolerance=simplify_tolerance,
                min_area=min_area,
            )

            if len(polygons) == 0:
                continue

            label = names_mapping[label_name]

            with tqdm.tqdm.external_write_mode():
                _LOGGER.debug(
                    f"[{mask_basename}] Found {len(polygons)} polygons for label '{label_name}'"
                )

            annotation = {
                "labelId": label.id,
                "fileId": dt_file.id,
                "sources": [
                    {
                        "type": "PaperSegmentations",
                        "data": {"pathData": polygons},
                    }
                ],
            }
            new_annotations.append(annotation)

        if len(new_annotations) > 0:
            api.execute(_CREATE_ANNOTATIONS, params={"annotations": new_annotations})
            with tqdm.tqdm.external_write_mode():
                _LOGGER.info(
                    f"[{mask_basename}] Successfully uploaded {len(new_annotations)} annotation(s)"
                )
        else:
            with tqdm.tqdm.external_write_mode():
                _LOGGER.warning(f"[{mask_basename}] No valid polygons found in mask")

    _LOGGER.info("Multi-label mask import complete.")
