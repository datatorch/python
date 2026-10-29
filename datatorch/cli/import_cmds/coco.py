import click


@click.command(
    "coco",
    help="Import a COCO formated file. By default the DataTorch server runs the "
    "import: it matches images to dataset files by name, creates missing labels "
    "and imports boxes, polygons and keypoints.",
)
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
    "-d",
    "--dataset",
    type=str,
    default=None,
    help="Name of the dataset to import into. Defaults to the project's only dataset.",
)
@click.option(
    "--client-side",
    is_flag=True,
    default=False,
    help="Import from this machine with pycocotools instead of on the server. "
    "Labels must already exist, keypoints are not imported, and the options "
    "below apply only in this mode.",
)
@click.option(
    "-m",
    "--max-iou",
    type=float,
    default=0.99,
    show_default=True,
    help="(--client-side) If an annotations matches this iou then it will not be added. Set to zero to disable. Disabling will significantly increase performance.",
)
@click.option(
    "-s",
    "--simplify",
    type=float,
    default=1.0,
    show_default=True,
    help="(--client-side) Simplification tolerance for new segmentation annotations. Set to zero to disable. Disabling will significantly increase performance.",
)
@click.option(
    "--no-segmentations",
    type=bool,
    flag_value=False,
    default=True,
    help="(--client-side) Flag to disable the import of coco segmentations.",
)
@click.option(
    "--import-bbox",
    type=bool,
    flag_value=True,
    default=False,
    help="(--client-side) Flag to enable to import of coco bounding boxes.",
)
def coco_cmd(
    file,
    project,
    dataset,
    client_side,
    max_iou,
    no_segmentations,
    import_bbox,
    simplify,
):
    if client_side:
        from datatorch.api.scripts.import_coco import import_coco

        import_coco(
            file,
            project,
            import_bbox=import_bbox,
            import_segmentation=no_segmentations,
            max_iou=max_iou,
            simplify_tolerance=simplify,
        )
        return

    from datatorch.api.scripts.import_coco_server import (
        CocoImportError,
        import_coco_server,
    )

    click.echo("Uploading and importing on the server...")
    try:
        result = import_coco_server(file, project, dataset_name=dataset)
    except CocoImportError as e:
        raise click.ClickException(f"COCO import failed:\n{e}")

    for warning in result["warnings"]:
        click.secho(f"warning: {warning}", fg="yellow")
    click.echo(
        f"Imported into dataset '{result['dataset']}': "
        f"{result['annotations_created']} annotations on "
        f"{result['files_processed']} files, "
        f"{result['labels_created']} new labels."
    )
