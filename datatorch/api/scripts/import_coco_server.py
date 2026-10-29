"""
COCO import run by the DataTorch server: the JSON is uploaded to the
project's default storage and the server's import job (createImport) maps
its images to dataset files by name, creates missing labels (with their
keypoint names and skeleton) and writes boxes, polygons and keypoints.
"""

import os
import re
import time
import uuid
import logging
from typing import List, Optional

import requests

from .. import ApiClient, Dataset, Project, Where

_LOGGER = logging.getLogger(__name__)

_CREATE_IMPORT = """
    mutation CreateImport($input: CreateImportInput!) {
        createImport(input: $input) { id }
    }
"""

_GET_IMPORT = """
    query GetImport($id: ID!) {
        import(id: $id) {
            annotationsCreated
            labelsCreated
            filesProcessed
            job { state logs { level message } }
        }
    }
"""

_DONE_STATES = ("SUCCESS", "FAILED", "CANCELED")


class CocoImportError(Exception):
    pass


def _plain(message: str) -> str:
    """Job log messages carry <b> tags for the web UI."""
    return re.sub(r"<[^>]+>", "", message)


def _pick_dataset(project: Project, dataset_name: Optional[str]) -> Dataset:
    if dataset_name:
        return project.dataset(dataset_name)
    datasets = project.datasets()
    if len(datasets) == 1:
        return datasets[0]
    names = [d.name for d in datasets]
    raise CocoImportError(
        f"Project has {len(datasets)} datasets, pass one with --dataset: {names}"
    )


def _upload(api: ApiClient, project: Project, file_path: str) -> str:
    """
    Uploads the COCO file as a project file and returns its id. The upload
    route returns no id and renames on a path clash, so the file goes into a
    fresh folder and is found again by its exact path.
    """
    # The server reads the file through whichever link holds it, so any link
    # works: DataTorch Storage when the project has it, else the first one.
    links = project.storage_links()
    if not links:
        raise CocoImportError("Project has no storage to upload the COCO file to")
    link = next((l for l in links if l.name == "DataTorch Storage"), links[0])
    folder = f"imports/{uuid.uuid4().hex}"
    name = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        r = requests.post(
            f"{api.api_url}/file/v1/upload/{link.id}",
            params={"path": folder, "import": "true"},
            files={"file": (name, f, "application/json")},
            headers={api.token_header: api._api_token},
        )
    if not r.ok:
        raise CocoImportError(f"Upload failed ({r.status_code}): {r.text[:300]}")

    files = project.files(Where(path=f"{folder}/{name}"), limit=2)
    if len(files) != 1:
        raise CocoImportError(f"Uploaded {name} but could not find it in the project")
    return files[0].id


def import_coco_server(
    file_path: str,
    project_string: str,
    dataset_name: Optional[str] = None,
    api: ApiClient = None,
    timeout: float = 3600,
    poll_seconds: float = 2,
) -> dict:
    """
    Imports a COCO file into a dataset on the server and waits for the job.
    Returns the import's counts and its warning messages; raises
    CocoImportError with the job's error messages if it fails.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"Provided path '{file_path}' is not a file.")

    if api is None:
        api = ApiClient()

    project: Project = api.project(project_string)
    dataset = _pick_dataset(project, dataset_name)

    _LOGGER.info("Uploading %s...", os.path.basename(file_path))
    file_id = _upload(api, project, file_path)

    import_id = api.execute(
        _CREATE_IMPORT,
        params={
            "input": {"datasetId": dataset.id, "fileId": file_id, "format": "COCO"}
        },
    )["createImport"]["id"]
    _LOGGER.info("Import %s queued for dataset '%s'.", import_id, dataset.name)

    deadline = time.time() + timeout
    while True:
        imp = api.execute(_GET_IMPORT, params={"id": import_id})["import"]
        state = imp["job"]["state"]
        if state in _DONE_STATES:
            break
        if time.time() > deadline:
            raise CocoImportError(
                f"Timed out waiting for import {import_id} (last state {state})"
            )
        time.sleep(poll_seconds)

    logs = imp["job"]["logs"] or []

    def messages(level: str) -> List[str]:
        return [_plain(log["message"]) for log in logs if log["level"] == level]

    if state != "SUCCESS":
        # The job logs one failure at several layers; the last is the cause.
        errors = messages("error") or [f"Import job ended {state}"]
        raise CocoImportError(errors[-1])

    return {
        "import_id": import_id,
        "dataset": dataset.name,
        "files_processed": imp["filesProcessed"],
        "labels_created": imp["labelsCreated"],
        "annotations_created": imp["annotationsCreated"],
        "warnings": messages("warn"),
    }
