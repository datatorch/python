import click


@click.command("coco", help="Import a COCO formated file.")
@click.option(
    "-f",
    "--file",
    type=click.Path(exists=True),
    prompt=True,
    help="Path to the json file containing coco annotations.",
)
@click.option(
    "-p",
    "--project",
    type=str,
    prompt=True,
    help="Namespace identifier or UUID of project (e.g. username/project)",
)
@click.option(
    "-m",
    "--max-iou",
    type=float,
    default=0.99,
    show_default=True,
    help="If an annotations matches this iou then it will not be added. Set to zero to disable. Disabling will significantly increase performance.",
)
@click.option(
    "-s",
    "--simplify",
    type=float,
    default=1.0,
    show_default=True,
    help="Simplification tolerance for new segmentation annotations. Set to zero to disable. Disabling will significantly increase performance.",
)
@click.option(
    "--no-segmentations",
    type=bool,
    flag_value=False,
    default=True,
    help="Flag to disable the import of coco segmentations.",
)
@click.option(
    "--import-bbox",
    type=bool,
    flag_value=True,
    default=False,
    help="Flag to enable to import of coco bounding boxes.",
)
def coco_cmd(file, project, max_iou, no_segmentations, import_bbox, simplify):
    from datatorch.api.scripts.import_coco import import_coco

    import_coco(
        file,
        project,
        import_bbox=import_bbox,
        import_segmentation=no_segmentations,
        max_iou=max_iou,
        simplify_tolerance=simplify,
    )
