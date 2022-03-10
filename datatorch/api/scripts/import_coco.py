import os
import sys
import copy
import numpy as np
import click
import logging
import pathlib
import tqdm

from typing import List
from .utils.simplify import simplify_points

from .. import ApiClient, BoundingBox, File, Where, Project


try:
    from pycocotools.coco import COCO
except:
    click.echo("Please install pycocotools should be installed:")
    click.echo("\t pip3 install pycocotools")

_LOGGER = logging.getLogger(__name__)

def points_to_segmentation(points: List[List[List[float]]]) -> List[List[float]]:
    """
    Converts from:
        [[[x1,y1], [x2,y2], ...]]
    to:
        [[x1,y1,x2,y2...]]
    """
    return [np.array(polygon).flatten().tolist() for polygon in points]


def segmentation_to_points(segmentation: List[List[float]]) -> List[List[List[float]]]:
    """
    Converts from:
        [[x1,y1,x2,y2...]]
    to:
        [[[x1,y1], [x2,y2], ...]]
    """
    return [np.reshape(polygon, (-1, 2)).tolist() for polygon in segmentation]


def bbox_iou(bb1o: BoundingBox, bb2o: BoundingBox):
    """ Calculate the Intersection over Union (IoU) of two bounding boxes. """
    bb1 = {
        "x1": bb1o.x,
        "y1": bb1o.y,
        "x2": bb1o.bottom_right[0],
        "y2": bb1o.bottom_right[1],
    }
    bb2 = {
        "x1": bb2o.x,
        "y1": bb2o.y,
        "x2": bb2o.bottom_right[0],
        "y2": bb2o.bottom_right[1],
    }

    x_left = max(bb1["x1"], bb2["x1"])
    y_top = max(bb1["y1"], bb2["y1"])
    x_right = min(bb1["x2"], bb2["x2"])
    y_bottom = min(bb1["y2"], bb2["y2"])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    bb1_area = (bb1["x2"] - bb1["x1"]) * (bb1["y2"] - bb1["y1"])
    bb2_area = (bb2["x2"] - bb2["x1"]) * (bb2["y2"] - bb2["y1"])

    return intersection_area / float(bb1_area + bb2_area - intersection_area)


def has_bbox(bbox: BoundingBox, bboxs: List[tuple], max_iou: float) -> bool:
    """
    Checks if the bounding box has a matching annotation in the bounding box
    list. Returns true if the iou of any segmentation in the list is over the
    max iou otherwise false.
    """
    for bb in bboxs:
        if bbox_iou(bbox, BoundingBox.xywh(*bb)) > max_iou:
            return True
    return False


def mask_iou(mask1, mask2):
    """ Calculate the Intersection over Union (IoU) of two np binary masks. """
    union = mask1 * mask2
    union_area = np.count_nonzero(union)
    if union_area == 0:
        return 0.0
    intersect = mask1 + mask2
    return union_area / np.count_nonzero(intersect)


def has_mask(anno_mask: np.array, masks: List[np.array], max_iou: float) -> bool:
    """
    Checks if the coco annotation has a matching annotation in the segmentation
    list. Returns true if the iou of any segmentation in the list is over the
    max iou otherwise false.
    """
    for mask in masks:
        iou = mask_iou(anno_mask, mask)
        if iou > max_iou:
            return True
    return False


def simplify_segmentation(segmentation: List[List[float]], tolerance: float = 1):
    """
    Simplifies an array of polygons in coco polygon format [[x1,y1,x2,y2,...]]
    """
    if tolerance == 0:
        return segmentation

    points_format = segmentation_to_points(segmentation)
    simplified = [
        simplify_points(polygon, tolerance=tolerance, highestQuality=False)
        for polygon in points_format
    ]
    simplified = [polygon for polygon in simplified if len(polygon) >= 6]
    return points_to_segmentation(simplified)


_CREATE_ANNOTATIONS = """
    mutation CreateAnnotations($annotations: [CreateAnnotationInput!]!) {
        createAnnotations(annotations: $annotations)
    }
"""


def import_coco(
    file_path: str,
    project_string: str,
    image_base_path: str = None,
    import_bbox: bool = False,
    import_segmentation: bool = True,
    max_iou: float = 0.99,
    simplify_tolerance: float = 0,
    ignore_annotations_with_ids: bool = True,
    api: ApiClient = None,
):
    if not import_segmentation and not import_bbox:
        _LOGGER.warning("Nothing to import. Both segmentation and bbox are disabled.")
        return

    if not os.path.isfile(file_path):
        raise ValueError(f"Provided path '{file_path}' is not a file.")

    check_iou: bool = max_iou != 0

    # Get DataTorch project information
    _LOGGER.debug("Connecting to DataTorch API.")
    if api is None:
        api = ApiClient()

    _LOGGER.debug("Loading Project Information.")
    if "/" in project_string:
        project: Project = api.project(*project_string.split("/", 1))
    else:
        project: Project = api.project(project_string)

    labels = project.labels()
    _LOGGER.debug("Project ID: %s", project.id)
    names_mapping = dict(((label.name, label) for label in labels))

    # Load coco file
    coco = COCO(file_path)
    coco_categories = coco.loadCats(coco.getCatIds())

    # Maps COCO Category ids to DataTorch ids. This is
    # done by matching label names.
    _LOGGER.info("Mapping coco labels to project labels...")
    label_mapping: dict = {}
    for category in coco_categories:
        name = category["name"]
        label_mapping[category["id"]] = datatorch_label = names_mapping.get(name)

        if not datatorch_label:
            _LOGGER.error("Could not find %s in project labels.", name)
            continue

    _LOGGER.info("Beginning annotation imports...")
    # Iterate each annotations to add them to datatorch
    coco_category_ids = label_mapping.keys()
    for image_id in tqdm.tqdm(coco.getImgIds(), unit='image', disable=None):
        (coco_image,) = coco.loadImgs(ids=image_id)
        image_name = coco_image["file_name"]

        if image_base_path is None:
            file_filter = Where(name=image_name)
        else:
            file_filter = Where(path=str(pathlib.PurePosixPath(image_base_path.strip('/')).joinpath(image_name)))
        dt_files = project.files(file_filter, limit=2)

        with tqdm.tqdm.external_write_mode():
            if len(dt_files) > 1:
                _LOGGER.error(f"Multiple files found of {image_name}, skipping")
                continue

            if len(dt_files) == 0:
                _LOGGER.error(f"No files found of {image_name}, skipping")
                continue

            dt_file: File = dt_files[0]
            _LOGGER.info(f"[{dt_file.name}] Successfully found file.")

            if dt_file.status == 'COMPLETED':
                _LOGGER.error(f"{image_name} is already marked as 'COMPLETED', skipping")
                continue

        coco_annotation_ids = coco.getAnnIds(
            catIds=coco_category_ids, imgIds=coco_image["id"]
        )
        coco_annotations = coco.loadAnns(ids=coco_annotation_ids)

        dt_segmentations = []
        dt_bbox = []

        if check_iou and len(coco_annotations) > 0:
            anno_copy = copy.deepcopy(coco_annotations[0])
            for anno in dt_file.annotations:
                for source in anno.sources:
                    if source.type == "PaperSegmentations":
                        anno_copy["segmentation"] = [
                            np.array(polygon).flatten() for polygon in source.path_data
                        ]
                        dt_mask = coco.annToMask(anno_copy)
                        dt_segmentations.append(dt_mask)
                    if source.type == "PaperBox":
                        dt_bbox.append(
                            [source.x, source.y, source.width, source.height]
                        )

        with tqdm.tqdm.external_write_mode():
            _LOGGER.debug(f"[{dt_file.name}] Importing {len(coco_annotations)} coco annotations.")
        new_annotations = []
        for anno in tqdm.tqdm(coco_annotations, unit='annotations', disable=None):
            if anno.get("datatorch_id") is not None and ignore_annotations_with_ids:
                with tqdm.tqdm.external_write_mode():
                    _LOGGER.warning(
                        f"[{dt_file.name}] Ignoring annotation as it already has a DataTorch ID ({anno.get('datatorch_id')})."
                    )
                continue

            label = label_mapping.get(anno["category_id"])
            if label is None:
                continue

            annotation = {"labelId": label.id, "fileId": dt_file.id, "sources": []}

            created_bbox = False
            created_segmentation = False

            if import_bbox and len(anno["bbox"]) == 4:
                bbox = BoundingBox.xywh(*anno["bbox"])
                if not check_iou or (
                    check_iou and not has_bbox(bbox, dt_bbox, max_iou)
                ):
                    with tqdm.tqdm.external_write_mode():
                        _LOGGER.debug(f"[{dt_file.name}] Adding new bounding box.")
                    created_bbox = True
                    annotation["sources"].append(
                        {
                            "type": "PaperBox",
                            "data": {
                                "x": bbox.x,
                                "y": bbox.y,
                                "width": bbox.width,
                                "height": bbox.height,
                            },
                        }
                    )

            # If the bbox was suppose to be created but wasn't, no point in
            # checking segmentation since it probably will be the same.
            if import_bbox and not created_bbox:
                continue

            if import_segmentation and len(anno["segmentation"]) > 0:
                anno["segmentation"] = simplify_segmentation(
                    anno["segmentation"], tolerance=simplify_tolerance
                )

                if len(anno["segmentation"]) > 0:
                    anno_mask = coco.annToMask(anno)

                    if not check_iou or (
                        check_iou and not has_mask(anno_mask, dt_segmentations, max_iou)
                    ):
                        with tqdm.tqdm.external_write_mode():
                            _LOGGER.debug(f"[{dt_file.name}] Adding new segmentation.")
                        path_data = segmentation_to_points(anno["segmentation"])
                        created_segmentation = True
                        annotation["sources"].append(
                            {
                                "type": "PaperSegmentations",
                                "data": {"pathData": path_data},
                            }
                        )

            if created_segmentation or created_bbox:
                new_annotations.append(annotation)

        if len(new_annotations) > 0:
            # Insert new annotations
            api.execute(_CREATE_ANNOTATIONS, params={"annotations": new_annotations})

        with tqdm.tqdm.external_write_mode():
            _LOGGER.info(f"[{dt_file.name}] Added {len(new_annotations)} annnotations.")
