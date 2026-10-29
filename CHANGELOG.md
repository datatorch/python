# Changelog

Notable changes to the `datatorch` python package (CLI, SDK and the runner
daemon). Versions are the tags on this repository and the releases on PyPI.

## 0.8.2 (2026-10-29)

### Added

- CLI: `datatorch import coco` runs the import on the server by default
  (upload, match images to dataset files by name, create missing labels
  with keypoint names and skeleton, write boxes, polygons and keypoints,
  then wait for the job and print its counts and warnings). `--dataset`
  picks the dataset when the project has more than one; the old
  pycocotools path stays behind `--client-side`.

### Fixed

- Runner: step inputs that merely contain `${{ ... }}` text no longer fail
  or get rewritten. The runner now renders only its own namespaces
  (`runner`/`agent`, `directory`, `machine`, `python`, `step`, `action`,
  `run`, `input`/`variable`); any other expression (`steps.*`, `inputs.*`,
  `jobs.*`, `secrets.*`, unknown names, or text that does not parse) is
  passed through exactly as written. Before, a `message` input
  that quoted an older error such as `${{ steps.fetch.output.body }}`
  failed the step with "'steps' is undefined" (seen on the org-root
  `watchdog-sense` pipeline, 2026-10-29). Objects and arrays were never
  rendered and still pass through untouched.

## 0.8.1 and earlier

See the git history and the GitHub releases.
