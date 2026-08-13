import click
from tqdm import tqdm

from datatorch.core import BASE_URL_API, user_settings
from datatorch.utils.url import normalize_api_url
from datatorch.api.pull import PullError, pull_project


@click.command(help="Download a project's dataset files (requires login).")
@click.argument("path")
@click.option(
    "--dataset",
    "-d",
    default=None,
    help="Dataset name (default: all non-archived datasets).",
)
@click.option(
    "--version",
    "-v",
    "version_name",
    default=None,
    help="Dataset version name (default: current files).",
)
@click.option(
    "--out",
    "-o",
    type=click.Path(file_okay=False),
    default=None,
    help="Output directory (default: ./<project>).",
)
@click.option(
    "--workers", "-w", default=8, show_default=True, help="Concurrent downloads."
)
@click.option("--force", is_flag=True, help="Re-download files that already exist.")
@click.option(
    "--annotations",
    "-a",
    "annotations_format",
    is_flag=False,
    flag_value="COCO",
    default=None,
    type=click.Choice(["COCO", "DataTorch", "YOLO"], case_sensitive=False),
    help="Also download the annotations artifact (bare flag = COCO). "
    "Saved as annotations.<format>.json (YOLO: .zip) next to the files.",
)
@click.option("--host", default=None, help="Url to a specific DataTorch instance.")
def pull(path, dataset, version_name, out, workers, force, annotations_format, host):
    """Pull OWNER/PROJECT files straight from storage — no export required.

    Requires a DataTorch account: run `datatorch login` (or set
    DATATORCH_API_KEY). Public projects stay browsable on the web without an
    account, but file downloads are account-gated.
    """
    parts = [p for p in path.split("/") if p]
    if len(parts) != 2:
        raise click.UsageError("PATH must look like <owner>/<project>.")
    owner, slug = parts

    api_url = normalize_api_url(host or user_settings.api_url or BASE_URL_API)
    api_key = user_settings.api_key

    # Downloads are account-gated server-side, so an anonymous pull can never
    # succeed — fail fast with a clear hint instead of enumerating then 401ing.
    if not api_key:
        raise click.ClickException(
            "Downloading requires a DataTorch account. Run 'datatorch login' "
            "(or set DATATORCH_API_KEY), then retry. Public projects are still "
            "browsable on the web without an account."
        )

    click.echo(
        f"Pulling {click.style(f'{owner}/{slug}', fg='blue', bold=True)} "
        f"from {api_url}"
    )

    progress = {"bar": None}

    def on_start(dataset_name: str, file_count: int):
        if progress["bar"] is not None:
            progress["bar"].close()
        click.echo(f"Dataset {click.style(dataset_name, bold=True)}: {file_count} file(s)")
        progress["bar"] = tqdm(total=file_count, unit="file") if file_count else None

    def on_file_done(outcome: str):
        bar = progress["bar"]
        if bar is None:
            return
        bar.update(1)
        counts = progress.setdefault("counts", {})
        counts[outcome] = counts.get(outcome, 0) + 1
        bar.set_postfix(counts, refresh=False)

    try:
        tally = pull_project(
            api_url,
            api_key,
            owner,
            slug,
            dataset=dataset,
            version=version_name,
            out=out,
            workers=workers,
            force=force,
            annotations=annotations_format,
            on_start=on_start,
            on_file_done=on_file_done,
        )
    except PullError as ex:
        if progress["bar"] is not None:
            progress["bar"].close()
        raise click.ClickException(str(ex))
    finally:
        if progress["bar"] is not None:
            progress["bar"].close()

    click.echo(
        f"Done: {tally['downloaded']} downloaded, {tally['skipped']} skipped, "
        f"{tally['missing']} missing, {tally['failed']} failed."
    )
    # Annotation failures warn but do not fail the exit code — the files
    # themselves landed, and a retry is one command away.
    for r in tally.get("annotations", []):
        if r["outcome"] == "downloaded":
            click.echo(
                f"Annotations ({annotations_format}): "
                f"{click.style(r['path'], bold=True)} · "
                f"{r['annotations']} annotations · {r['labels']} labels"
            )
        else:
            click.echo(
                click.style(
                    f"Annotations ({annotations_format}) failed for "
                    f"{r['dataset']}: {r.get('detail', 'unknown error')}",
                    fg="yellow",
                )
            )
    if tally["missing"]:
        click.echo(
            click.style(
                f"{tally['missing']} file(s) in this selection no longer exist "
                "in storage (expected for old versions).",
                fg="yellow",
            )
        )
    if tally.get("aborted"):
        click.echo(click.style("Interrupted — re-run to resume.", fg="yellow"))
        raise SystemExit(130)
    if tally["failed"]:
        raise SystemExit(1)
