'''
This script imports COCO formated annotations into DataTorch
'''
import numpy as np

from pycocotools.coco import COCO
from datatorch.api import (
    ApiClient,
    Where,
    Label,
    Annotation,
    Segmentations,
    BoundingBox,
)



def print_project(project):
    print("=" * 50)
    print(f"Project: {project.name}")
    names = [label.name for label in labels]
    print(f'Labels: {" ".join(names)}')
    print("=" * 50)


if __name__ == "__main__":

    # ----- Settings -----

    # DataTorch project ID
    # You can obtain this by going into the settings view of the project
    project_id = "DATATORCH_PROJECT_ID"
    
    # Path to annotation file
    anno_file = "path/to/coco"

    # Only add annotations above this score will be imported. This is done by
    # check for the property 'score' on each annotation to determine if it
    # should be imported
    min_score = 0.8

    # If both import options are enabled the script will create two sources per
    # annotations, one as a segmentation the other as a bounding box.

    # Import bounding boxes from the coco format
    import_bbox = False

    # Import segmentations from the coco format
    import_segmentation = True

    # ----- Script -----

    # Connect to DataTorch
    api = ApiClient()
    project = api.project(project_id)
    labels = project.labels()

    print_project(project)

    def category_in_project(name: str) -> Label:
        """ Returns category in project """
        for cat in labels:
            if cat.name.lower() == name.lower():
                return cat
        return None

    # Load coco categories
    coco = COCO(anno_file)
    cats = coco.loadCats(coco.getCatIds())
    names = [cat["name"] for cat in cats]

    label_maping = {}
    for cat in cats:
        name = cat["name"]
        found = category_in_project(name)

        if not found:
            print(f'label "{name}" not found in project')
        else:
            label_maping[cat["id"]] = found

    print(f'COCO Categories: {" ".join(names)}')

    for img_id in coco.getImgIds():
        (img,) = coco.loadImgs(img_id)
        name = img["file_name"]

        find_by_name = Where(name=name, mimetype__starts_with="image")
        dt_files = project.files(find_by_name)
        files_count = len(dt_files)

        if files_count > 1:
            print(f"\nMultiple files found with name {name}, skipping")
            continue

        if files_count == 0:
            print(f"\nNo files found with name {name}, skipping")
            continue

        print(f"\n{name} found. Importing annotations")
        dt_file = dt_files[0]

        # load file annotations
        anno_ids = coco.getAnnIds(imgIds=img["id"])
        annos = coco.loadAnns(anno_ids)

        for anno in annos:
            # Create annotation
            if anno.get("datatorch_id") is not None:
                print(f'Annotation {anno["id"]} already exists in DataTorch, skipping')

            score = anno.get("score", 1)
            if score < min_score:
                continue

            label = label_maping[anno["category_id"]]
            if label is None:
                continue

            dt_anno = Annotation(label=label)
            if import_bbox:
                bbox = BoundingBox.xywh(*anno["bbox"])
                dt_anno.add(bbox)
            
            if import_segmentation:
                polygons = anno["segmentation"]
                # Format segmentation to the correct DataTorch format which is:
                # [ 
                #   [ [x1,y1], [x2,y2], ... ],
                #   [ [x1,y1], [x2,y2], ... ]
                # ]
                path_data = [np.reshape(polygon, (-1, 2)) for polygon in polygons]
                segmentation = Segmentations(path_data=path_data)
                dt_anno.add(segmentation)

            dt_file.add(dt_anno)
