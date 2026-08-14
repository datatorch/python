"""
Bulk-download a project's dataset files directly via GraphQL + the file API.

Used by `datatorch pull`. Deliberately does NOT use `datatorch.api.Client`:
that client runs a schema introspection on init (a wasted roundtrip that can
fail for anonymous users) and silently overrides a passed api_url with the
stored user settings. A plain requests.Session covers the four fixed queries
this module needs and shares its connection pool with the file downloads.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Optional

import requests
from requests.adapters import HTTPAdapter

API_KEY_HEADER = "datatorch-api-key"
CHUNK_SIZE = 1024 * 1024  # 1 MiB
PAGE_SIZE = 500  # server clamps version pages at 500
MAX_ATTEMPTS = 4  # per-file network retries within a run (resumes each time)

_AUTH_ERROR_RE = re.compile(
    r"permission|logged in|authenticated|authorized", re.IGNORECASE
)

PROJECT_QUERY = """
query PullProject($login: String!, $slug: String!) {
  project(login: $login, slug: $slug) {
    id
    slug
    datasets {
      nodes { id name isArchived }
      totalCount
    }
  }
}
"""

VERSIONS_QUERY = """
query PullDatasetVersions($id: ID!) {
  dataset: datasetById(id: $id) {
    id
    name
    versions { id name locked cutAt }
  }
}
"""

LIVE_FILES_QUERY = """
query PullDatasetFiles($id: ID!, $first: Int!, $after: String) {
  dataset: datasetById(id: $id) {
    filesCursor(input: { first: $first, after: $after, order: NAME }) {
      nodes { id name path kilobytes }
      pageInfo { endCursor hasNextPage }
      totalCount
    }
  }
}
"""

VERSION_FILES_QUERY = """
query PullVersionFiles($id: ID!, $page: Int!, $perPage: Int!) {
  datasetVersion(id: $id) {
    id
    name
    files(page: $page, perPage: $perPage) { id fileId name path md5Hash }
  }
}
"""

CREATE_ANNOTATIONS_MUTATION = """
mutation PullCreateAnnotations($datasetId: ID!, $versionId: ID, $format: ExportFormat!) {
  createDatasetAnnotations(
    datasetId: $datasetId
    versionId: $versionId
    format: $format
  ) {
    id
    job { state }
  }
}
"""

GET_ANNOTATIONS_QUERY = """
query PullGetAnnotations($datasetId: ID!, $versionId: ID, $format: ExportFormat!) {
  datasetAnnotations(datasetId: $datasetId, versionId: $versionId, format: $format) {
    id
    annotationCount
    labelCount
    job { state }
    artifact { id name }
  }
}
"""

# Stable local filenames so downstream tooling can rely on the path; the
# server artifact name embeds a build number that would churn on rebuilds.
ANNOTATION_FILENAMES = {
    "COCO": "annotations.coco.json",
    "DataTorch": "annotations.datatorch.json",
    "YOLO": "annotations.yolo.zip",
}

ANNOTATIONS_BUILD_TIMEOUT = 600  # seconds


class PullError(Exception):
    """User-facing pull failure (bad input, auth, server error)."""


@dataclass
class PullFile:
    file_id: str  # live File id — what /api/file/v1/<id> resolves
    rel_path: str  # sanitized path relative to the output dir
    kilobytes: Optional[int] = None  # live files only (KB, rounded)
    md5: Optional[str] = None  # version snapshot files only


def safe_relpath(path: str, fallback: str) -> str:
    """
    Sanitize a server-provided path into a safe relative path: no absolute
    paths, no '..', no drive letters. Falls back to `fallback` (sanitized
    name or file id) when nothing survives.
    """
    segments = []
    for seg in re.split(r"[/\\]+", path or ""):
        if seg in ("", ".", ".."):
            continue
        if re.match(r"^[A-Za-z]:$", seg):
            continue
        segments.append(seg)
    return os.path.join(*segments) if segments else fallback


def _md5_of(path: str) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


class _PullSession:
    def __init__(self, api_url: str, api_key: Optional[str], workers: int):
        self.api_url = api_url.rstrip("/")
        self.graphql_url = f"{self.api_url}/graphql"
        self.headers = {API_KEY_HEADER: api_key} if api_key else {}
        self.anonymous = not api_key
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=max(workers, 4), pool_maxsize=max(workers, 4)
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def graphql(self, query: str, variables: dict) -> dict:
        try:
            r = self.session.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=60,
            )
        except requests.RequestException as ex:
            raise PullError(f"Could not reach {self.graphql_url}: {ex}")
        if r.status_code >= 400:
            raise PullError(f"API returned HTTP {r.status_code} for GraphQL query.")
        body = r.json()
        errors = body.get("errors")
        if errors:
            message = "; ".join(e.get("message", "unknown error") for e in errors)
            if _AUTH_ERROR_RE.search(message):
                raise PullError(self._auth_hint(message))
            raise PullError(message)
        return body.get("data") or {}

    def _auth_hint(self, message: str) -> str:
        hint = (
            "This project requires authentication (or does not exist)."
            if self.anonymous
            else "Your API key does not have access to this project."
        )
        return f"{hint} Run 'datatorch login' and retry. ({message})"


def _resolve_project(api: _PullSession, owner: str, slug: str) -> dict:
    data = _none_safe(api.graphql(PROJECT_QUERY, {"login": owner, "slug": slug}))
    project = data.get("project")
    if not project:
        raise PullError(
            f"Project '{owner}/{slug}' was not found"
            + (
                " (private projects require 'datatorch login')."
                if api.anonymous
                else " or your key has no access."
            )
        )
    return project


def _none_safe(value: Optional[dict]) -> dict:
    return value or {}


def _select_datasets(project: dict, dataset_name: Optional[str]) -> list:
    nodes = [d for d in (project.get("datasets") or {}).get("nodes") or [] if d]
    if dataset_name is None:
        active = [d for d in nodes if not d.get("isArchived")]
        return active
    exact = [d for d in nodes if d.get("name") == dataset_name]
    if len(exact) == 1:
        return exact
    insensitive = [
        d for d in nodes if d.get("name", "").lower() == dataset_name.lower()
    ]
    if len(insensitive) == 1:
        return insensitive
    names = ", ".join(sorted(d.get("name", "?") for d in nodes)) or "(none)"
    raise PullError(f"Dataset '{dataset_name}' not found. Available datasets: {names}")


def _resolve_version(api: _PullSession, dataset: dict, version_name: str) -> dict:
    data = api.graphql(VERSIONS_QUERY, {"id": dataset["id"]})
    versions = [
        v
        for v in (_none_safe(data.get("dataset")).get("versions") or [])
        if v and not v.get("name", "").startswith("unlock:")
    ]
    match = [v for v in versions if v.get("name") == version_name]
    if len(match) == 1:
        return match[0]
    names = ", ".join(sorted(v.get("name", "?") for v in versions)) or "(none)"
    raise PullError(
        f"Version '{version_name}' not found on dataset "
        f"'{dataset.get('name')}'. Available versions: {names}"
    )


def _list_live_files(api: _PullSession, dataset_id: str) -> list:
    files: list = []
    after: Optional[str] = None
    while True:
        data = api.graphql(
            LIVE_FILES_QUERY,
            {"id": dataset_id, "first": PAGE_SIZE, "after": after},
        )
        cursor = _none_safe(_none_safe(data.get("dataset")).get("filesCursor"))
        nodes = [n for n in cursor.get("nodes") or [] if n]
        for node in nodes:
            files.append(
                PullFile(
                    file_id=node["id"],
                    rel_path=safe_relpath(
                        node.get("path") or "",
                        safe_relpath(node.get("name") or "", node["id"]),
                    ),
                    kilobytes=node.get("kilobytes"),
                )
            )
        page_info = _none_safe(cursor.get("pageInfo"))
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        if not after:
            break
    return files


def _list_version_files(api: _PullSession, version_id: str) -> list:
    files: list = []
    page = 0
    while True:
        data = api.graphql(
            VERSION_FILES_QUERY,
            {"id": version_id, "page": page, "perPage": PAGE_SIZE},
        )
        rows = [
            r for r in (_none_safe(data.get("datasetVersion")).get("files") or []) if r
        ]
        for row in rows:
            files.append(
                PullFile(
                    file_id=row["fileId"],
                    rel_path=safe_relpath(
                        row.get("path") or "",
                        safe_relpath(row.get("name") or "", row["fileId"]),
                    ),
                    md5=row.get("md5Hash"),
                )
            )
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return files


def _dedupe_targets(files: list) -> None:
    """Two files can sanitize to the same target — suffix the collisions."""
    seen: dict = {}
    for pf in files:
        key = pf.rel_path.lower()
        if key in seen:
            root, ext = os.path.splitext(pf.rel_path)
            pf.rel_path = f"{root}_{pf.file_id[:8]}{ext}"
        seen[pf.rel_path.lower()] = True


def _should_skip(pf: PullFile, target: str, force: bool) -> bool:
    if force or not os.path.isfile(target):
        return False
    if pf.md5:
        try:
            return _md5_of(target) == pf.md5
        except OSError:
            return False
    if pf.kilobytes:
        try:
            size_kb = os.path.getsize(target) / 1024
        except OSError:
            return False
        # Server-side kilobytes are rounded at ingest and drift slightly from
        # the actual blob; downloads are atomic (.part + rename) so a local
        # file is never truncated. Use a relative tolerance — this catches
        # real content changes, not rounding noise.
        return abs(size_kb - pf.kilobytes) <= max(2.0, pf.kilobytes * 0.002)
    # No hash or size to validate against — existence is the best we have.
    return True


def _download_one(
    api: _PullSession,
    pf: PullFile,
    out_dir: str,
    force: bool,
    abort: threading.Event,
) -> str:
    """Returns 'downloaded' | 'skipped' | 'missing' | 'failed' | 'aborted'."""
    if abort.is_set():
        return "aborted"

    target = os.path.abspath(os.path.join(out_dir, pf.rel_path))
    out_root = os.path.abspath(out_dir)
    # Final containment defense against hostile server-provided paths.
    if not (target == out_root or target.startswith(out_root + os.sep)):
        return "failed"

    if _should_skip(pf, target, force):
        return "skipped"

    url = f"{api.api_url}/file/v1/{pf.file_id}/?download=true&stream=true"
    part = target + ".part"
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    # --force means re-fetch from scratch, so drop any stale partial.
    if force:
        _safe_remove(part)

    # Retry loop: each attempt resumes from whatever bytes already landed in
    # .part via an HTTP Range request, so a dropped connection (or a presigned
    # URL that expired mid-transfer on a huge file) costs only the unfetched
    # tail, not the whole file. The .part is preserved across attempts AND
    # across runs — only success (rename), a missing file, or a hard error
    # clears it. The request goes to the API, which 302-redirects to storage;
    # requests carries the Range header through the redirect, and cloud
    # providers honor it (local storage ignores it and returns the full body,
    # which we handle by restarting the file).
    backoff = 1.0
    for attempt in range(MAX_ATTEMPTS):
        if abort.is_set():
            return "aborted"

        resume_from = 0
        try:
            resume_from = os.path.getsize(part)
        except OSError:
            resume_from = 0
        headers = dict(api.headers)
        if resume_from:
            headers["Range"] = f"bytes={resume_from}-"

        try:
            with api.session.get(
                url, headers=headers, stream=True, timeout=(10, 300)
            ) as r:
                if r.status_code == 404:
                    _safe_remove(part)
                    return "missing"
                if r.status_code in (401, 403):
                    abort.set()
                    if api.anonymous:
                        raise PullError(
                            "Downloading files requires a DataTorch account. "
                            "Run 'datatorch login' (or set DATATORCH_API_KEY) "
                            "and retry."
                        )
                    raise PullError(api._auth_hint(f"HTTP {r.status_code} on download"))
                if r.status_code == 416:
                    # Our .part is already >= the object; discard and re-fetch.
                    _safe_remove(part)
                    continue
                if r.status_code >= 400:
                    raise requests.RequestException(f"HTTP {r.status_code}")

                # 206 => range honored, append. Anything else (200) => full
                # body, so start the file over even if we had a partial.
                append = resume_from > 0 and r.status_code == 206
                with open(part, "ab" if append else "wb") as f:
                    for chunk in r.iter_content(CHUNK_SIZE):
                        if abort.is_set():
                            return "aborted"  # keep .part to resume later
                        f.write(chunk)
            os.replace(part, target)
            return "downloaded"
        except PullError:
            raise
        except (requests.RequestException, OSError):
            # Keep .part so the next attempt (and next run) resumes from here.
            if attempt + 1 >= MAX_ATTEMPTS:
                return "failed"
            # Interruptible backoff — wakes immediately on Ctrl-C.
            if abort.wait(backoff):
                return "aborted"
            backoff = min(backoff * 2, 15.0)

    return "failed"


def _pull_annotations(
    api: _PullSession,
    dataset_id: str,
    version_id: Optional[str],
    fmt: str,
    out_dir: str,
) -> dict:
    """
    Ensure + poll + download the dataset's annotations artifact. Returns
    {'outcome': 'downloaded', 'path', 'annotations', 'labels'} or
    {'outcome': 'failed', 'detail'}.
    """
    variables = {"datasetId": dataset_id, "versionId": version_id, "format": fmt}
    try:
        # Idempotent server-side: returns the fresh artifact, the in-flight
        # build, or enqueues one (subject to the server's build rate limit).
        api.graphql(CREATE_ANNOTATIONS_MUTATION, variables)

        deadline = time.time() + ANNOTATIONS_BUILD_TIMEOUT
        while True:
            row = api.graphql(GET_ANNOTATIONS_QUERY, variables).get(
                "datasetAnnotations"
            )
            state = (((row or {}).get("job") or {}).get("state") or "").upper()
            if state == "SUCCESS" and (row or {}).get("artifact"):
                break
            if state in ("FAILED", "CANCELED"):
                return {"outcome": "failed", "detail": "server build failed"}
            if time.time() > deadline:
                return {"outcome": "failed", "detail": "timed out waiting for build"}
            time.sleep(2)

        artifact = row["artifact"]
        target = os.path.join(out_dir, ANNOTATION_FILENAMES[fmt])
        part = target + ".part"
        url = f"{api.api_url}/file/v1/{artifact['id']}/?download=true&stream=true"
        with api.session.get(
            url, headers=api.headers, stream=True, timeout=(10, 300)
        ) as r:
            r.raise_for_status()
            os.makedirs(out_dir or ".", exist_ok=True)
            with open(part, "wb") as f:
                for chunk in r.iter_content(CHUNK_SIZE):
                    f.write(chunk)
        os.replace(part, target)
        return {
            "outcome": "downloaded",
            "path": target,
            "annotations": (row or {}).get("annotationCount", 0),
            "labels": (row or {}).get("labelCount", 0),
        }
    except (PullError, requests.RequestException, OSError) as ex:
        return {"outcome": "failed", "detail": str(ex)}


def pull_project(
    api_url: str,
    api_key: Optional[str],
    owner: str,
    slug: str,
    dataset: Optional[str] = None,
    version: Optional[str] = None,
    out: Optional[str] = None,
    workers: int = 8,
    force: bool = False,
    annotations: Optional[str] = None,
    on_start: Optional[Callable[[str, int], None]] = None,
    on_file_done: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Download a project's dataset files. Returns a tally dict:
    {'downloaded': n, 'skipped': n, 'missing': n, 'failed': n, 'aborted': bool}

    on_start(dataset_name, file_count) fires per dataset before downloads;
    on_file_done(outcome) fires per completed file (any outcome).
    """
    api = _PullSession(api_url, api_key, workers)
    project = _resolve_project(api, owner, slug)
    out_dir = out or f"./{project.get('slug') or slug}"

    datasets = _select_datasets(project, dataset)
    if not datasets:
        raise PullError("This project has no (non-archived) datasets.")
    if version and dataset is None and len(datasets) > 1:
        raise PullError(
            "--version requires --dataset when the project has several datasets."
        )
    multi = dataset is None and len(datasets) > 1

    tally = {"downloaded": 0, "skipped": 0, "missing": 0, "failed": 0}
    tally["annotations"] = []
    abort = threading.Event()
    aborted = False

    try:
        for ds in datasets:
            version_id: Optional[str] = None
            if version:
                v = _resolve_version(api, ds, version)
                version_id = v["id"]
                files = _list_version_files(api, version_id)
            else:
                files = _list_live_files(api, ds["id"])

            ds_out = (
                os.path.join(out_dir, safe_relpath(ds.get("name") or "", ds["id"]))
                if multi
                else out_dir
            )
            _dedupe_targets(files)
            if on_start:
                on_start(ds.get("name") or "?", len(files))

            if files:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [
                        pool.submit(_download_one, api, pf, ds_out, force, abort)
                        for pf in files
                    ]
                    try:
                        for future in as_completed(futures):
                            outcome = future.result()  # re-raises PullError
                            if outcome in tally:
                                tally[outcome] += 1
                            if on_file_done:
                                on_file_done(outcome)
                    except KeyboardInterrupt:
                        abort.set()
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise

            if annotations and not abort.is_set():
                result = _pull_annotations(
                    api, ds["id"], version_id, annotations, ds_out
                )
                tally["annotations"].append(
                    {"dataset": ds.get("name") or "?", **result}
                )
    except KeyboardInterrupt:
        aborted = True

    tally["aborted"] = aborted
    return tally
