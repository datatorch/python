"""
This script imports binary mask annotations from a Kaggle nail semantic segmentation
dataset into DataTorch.

Dataset structure (typical for segmentation datasets):
    NailSegmentationDatasetV2/
    ├── train/
    │   ├── images/      <- Original images
    │   └── masks/       <- Binary mask images (same filenames)
    ├── test/
    │   ├── images/
    │   └── masks/
    └── val/
        ├── images/
        └── masks/

Usage:
    1. Create a project in DataTorch with a label (e.g., "nail")
    2. Create a dataset in the project (e.g., "training")
    3. Set your project_id, dataset_name, and label_name below
    4. Run this script - it will upload images first, then import masks
"""

import os
import kagglehub
from datatorch.api import ApiClient

if __name__ == "__main__":
    # ----- Settings -----

    # DataTorch project identifier
    # Can be "username/project-name" or the project UUID
    project_id = "mnguyen/nail-dataset2"

    # Dataset name in your DataTorch project to import files into
    # This must be created in the project before running
    dataset_name = "training"

    # Label name in your DataTorch project for the nail annotations
    # This must match a label you've already created in the project
    label_name = "nail"

    # Download dataset from Kaggle
    print("Downloading dataset from Kaggle...")
    dataset_path = kagglehub.dataset_download(
        "muhammadhammad261/nail-segmentation-dataset"
    )
    base_path = os.path.join(dataset_path, "NailSegmentationDatasetV2", "train")

    # Paths to images and masks
    images_folder = os.path.join(base_path, "images")
    masks_folder = os.path.join(base_path, "masks")

    print(f"Dataset downloaded to: {dataset_path}")
    print(f"Images folder: {images_folder}")
    print(f"Masks folder: {masks_folder}")

    # List what's in the folders to verify structure
    if os.path.exists(masks_folder):
        mask_files = os.listdir(masks_folder)[:5]
        print(f"\nSample mask files: {mask_files}")
    else:
        print(f"\nContents of {base_path}:")
        print(os.listdir(base_path))
        print("\nPlease update masks_folder path based on actual structure.")
        exit(1)

    if os.path.exists(images_folder):
        image_files = os.listdir(images_folder)[:5]
        print(f"Sample image files: {image_files}")
    else:
        print(f"\nImages folder not found at {images_folder}")
        print(f"Contents of {base_path}:")
        print(os.listdir(base_path))
        print("\nPlease update images_folder path based on actual structure.")
        exit(1)

    # ----- Step 1: Upload Images to DataTorch -----

    print("\n" + "=" * 50)
    print("Step 1: Uploading images to DataTorch...")
    print("=" * 50)

    # Connect to DataTorch
    api = ApiClient()

    try:
        project = api.project(project_id)
    except Exception as e:
        print(f"\nError: Could not find project '{project_id}'.")
        print(f"Please check the project ID and try again.")
        print(f"Details: {e}")
        exit(1)

    print(f"Project: {project.name}")

    try:
        dataset = project.dataset(dataset_name)
    except ValueError as e:
        print(f"\nError: {e}")
        print(f"\nTo create a dataset:")
        print(f"  1. Go to your project in DataTorch")
        print(f"  2. Click 'Datasets' in the sidebar")
        print(f"  3. Click 'Create Dataset' and name it '{dataset_name}'")
        exit(1)

    print(f"Dataset: {dataset.name}")

    try:
        storage = project.storage_link_default()
    except Exception as e:
        print(f"\nError: Could not get default storage for project.")
        print(f"Please check your project has a storage configured.")
        print(f"Details: {e}")
        exit(1)

    print(f"Storage: {storage.name}")

    # Validate label exists
    labels = project.labels()
    label_names = [l.name for l in labels]
    if label_name not in label_names:
        print(f"\nError: Label '{label_name}' not found in project.")
        print(f"Available labels: {label_names}")
        print(f"\nTo create a label:")
        print(f"  1. Go to your project in DataTorch")
        print(f"  2. Click 'Labels' in the sidebar")
        print(f"  3. Click 'Create Label' and name it '{label_name}'")
        exit(1)

    print(f"Label: {label_name}")

    # Get list of image files
    image_file_list = [
        f
        for f in os.listdir(images_folder)
        if os.path.isfile(os.path.join(images_folder, f))
    ]

    print(f"\nUploading {len(image_file_list)} images...")

    # Upload each image
    for i, filename in enumerate(image_file_list):
        filepath = os.path.join(images_folder, filename)
        print(f"  [{i+1}/{len(image_file_list)}] Uploading {filename}...", end="\r")

        try:
            with open(filepath, "rb") as f:
                api.upload_to_filesource(
                    project=project,
                    file=f,
                    storageId=storage.id,
                    storageFolderName=None,
                    dataset=dataset,
                )
        except Exception as e:
            print(f"\n  Error uploading {filename}: {e}")

    print(f"\n  Uploaded {len(image_file_list)} images successfully!")

    # ----- Step 2: Import Annotations from Masks -----

    print("\n" + "=" * 50)
    print("Step 2: Importing annotations from masks...")
    print("=" * 50)

    from datatorch.api.scripts.import_binmask import import_binmask

    import_binmask(
        mask_folder=masks_folder,
        project_string=project_id,
        label_name=label_name,
        # If your mask files have a suffix like "image_mask.png", specify it here
        # Otherwise set to empty string if masks have same name as images
        mask_suffix="",  # e.g., "_mask" or "" if no suffix
        # Polygon simplification (higher = simpler polygons, smaller file size)
        simplify_tolerance=1.0,
        # Minimum contour area to include (filters out noise)
        min_area=100.0,
        # Set to True if the mask is inverted (black = object, white = background)
        invert_mask=False,
        # Skip files that already have annotations (useful for resuming)
        skip_annotated=True,
        api=api,
    )

    print("\nImport complete!")
