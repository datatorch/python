import click


@click.command(
    "pixmask", help="Import pixel masks from a folder as polygon annotations."
)
# Required options (prompted)
@click.option(
    "-f",
    "--folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    prompt=True,
    help="Path to folder containing pixel mask images.",
)
@click.option(
    "-p",
    "--project",
    type=str,
    prompt=True,
    help="Namespace identifier or UUID of project (e.g. username/project)",
)
# Common options
@click.option(
    "-l",
    "--label",
    type=str,
    default=None,
    help="Label name to assign to all annotations. If not provided, will try to detect from filename.",
)
@click.option(
    "--suffix",
    type=str,
    default="_mask",
    show_default=True,
    help="Suffix to strip from mask filenames when matching to source images.",
)
# Path matching
@click.option(
    "-b",
    "--base-path",
    type=str,
    default=None,
    help="Base path for matching files in DataTorch (optional).",
)
# Processing options
@click.option(
    "--simplify",
    type=float,
    default=1.0,
    show_default=True,
    help="Simplification tolerance for polygon annotations. Set to 0 to disable.",
)
@click.option(
    "--min-area",
    type=float,
    default=100.0,
    show_default=True,
    help="Minimum contour area to include as annotation.",
)
# Boolean flags
@click.option(
    "--invert",
    is_flag=True,
    default=False,
    help="Invert the pixel mask before processing (swap foreground/background).",
)
@click.option(
    "--skip",
    is_flag=True,
    default=False,
    help="Skip files that already have annotations.",
)
def pixmask_cmd(
    folder, project, label, suffix, base_path, simplify, min_area, invert, skip
):
    """Import pixel masks from a folder into DataTorch as polygon annotations.

    Images must already be uploaded to DataTorch before running this command.
    Use `datatorch upload folder` to upload images first.

    Pixel masks should be grayscale images where white (255) represents the object
    and black (0) represents the background. The mask filenames should match
    the corresponding image files in your DataTorch project.

    Naming conventions supported:

    \b
    - imagename_mask.png -> matches 'imagename.png/jpg/etc'
    - imagename_labelname_mask.png -> matches 'imagename.png' with label 'labelname'
    - imagename.png -> matches 'imagename.png' (when --suffix is empty)

    Examples:

    \b
    # First upload images, then import masks
    $ datatorch upload folder ./images project-id
    $ datatorch import pixmask -f ./masks -p project-id -l "person"

    \b
    # Import masks where label is in filename
    $ datatorch import pixmask -f ./masks -p username/project

    \b
    # Resume an interrupted import (skip already annotated files)
    $ datatorch import pixmask -f ./masks -p myproject -l "nail" --skip
    """
    from datatorch.api.scripts.import_pixmask import import_pixmask

    import_pixmask(
        mask_folder=folder,
        project_string=project,
        label_name=label,
        image_base_path=base_path,
        mask_suffix=suffix,
        simplify_tolerance=simplify,
        min_area=min_area,
        invert_mask=invert,
        skip_annotated=skip,
    )
