from datatorch.api import (
    ApiClient,
    Where,
    Label,
    Annotation,
    Segmentations,
    BoundingBox,
)

from pycocotools.coco import COCO


def print_project(project):
    print("=" * 50)
    print(f"Project: {project.name}")
    names = [label.name for label in labels]
    print(f'Labels: {" ".join(names)}')
    print("=" * 50)


if __name__ == "__main__":

    # DataTorch project ID
    project_id = "DATATORCH_PROJECT_ID"
    # Path to annotation file
    anno_file = "path/to/coco"
    # Only add annotations above this score
    min_score = 0.8

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

            score = anno.get("score")
            if anno.get("score") is not None and score < min_score:
                continue

            label = label_maping[anno["category_id"]]
            if label is None:
                continue

            dt_anno = Annotation(label=label)
            bbox = BoundingBox.xywh(*anno["bbox"])
            dt_anno.add(bbox)
            print(bbox.__dict__)
            dt_file.add(dt_anno)
