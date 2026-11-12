# Changelog

Notable changes to the `datatorch` python package (CLI, SDK and the runner
daemon). Versions are the tags on this repository and the releases on PyPI.

## 0.8.4 (2026-11-12)

### Fixed

- Runner: a step that is stopped (its timeout ran out, the run was
  canceled, or the runner is shutting down) now stops everything it
  started, not only the shell that wraps its command. Before, the runner
  killed that one shell and whatever ran under it carried on with nobody
  watching: on 2026-11-11 the org-root `dataset-scout` seed step hit its
  240 minute timeout and its `claude` process kept working against the
  server for another 40 minutes. Each step now runs in its own session
  and process group. On a stop the runner notes every process under the
  step (one that moved to a session of its own is still found, by
  parentage), sends them SIGTERM so a program that manages children of
  its own can stop them, and kills whatever is still running 5 seconds
  later (`TERMINATE_GRACE_SECONDS`). Windows is unchanged: the direct
  child is terminated as before.

### Changed

- Runner: because a step has its own session, Ctrl-C in the terminal the
  runner was started from reaches the runner alone. The runner then stops
  its running steps itself, through the path above.

## 0.8.3 (2026-11-09)

### Fixed

- Runner: a dropped websocket no longer cancels the steps the runner is
  running. Before, any transport failure (`no close frame received or
  sent`, `keepalive ping timeout`, a rolling API deploy) tore down every
  running step before reconnecting, so a four-second blip killed hours of
  work (the org-root `dataset-scout` seed step, 2026-11-09, three drops in
  eighteen minutes). Now only the connection's own tasks (monitoring, the
  stop-signal and command listeners) are rebuilt on reconnect. A step that
  finishes while the runner is disconnected holds its result (its last log
  lines and the completion) until the connection is back and retries the
  report for up to 10 minutes; after that it logs the loss and drops the
  result. A completion the server no longer accepts (the step was failed,
  canceled or timed out there while the runner was offline) is logged and
  absorbed, never a crash. A real shutdown (Ctrl-C, SIGTERM) still cancels
  running steps as before.
- Runner: finished step tasks are removed from the daemon's task list, so
  the shutdown path and its "Exiting N active step(s)" line count the
  steps really in flight (the list only ever grew before: 71, 74, 77 across
  three reconnects on the same day).
- Runner: a claim that fails because the connection just dropped is logged
  and the step is left for the next connection to pick up (the server
  offers unclaimed steps again on connect), instead of dying silently.
- Runner: a step whose final log upload fails is still reported as
  finished; the lines go out with the completion.

### Changed

- Runner: a step's log lines stream to the server every 3 seconds while
  the step runs (before, one batch was sent 10 seconds in and the rest
  only at the end), so the run page and a chat turn's live view show
  them as they are printed. A batch that fails to send is kept and goes
  out with the next one.
- Runner: `datatorch.runner.serve_forever(client, transport)` is the
  connect-serve-reconnect loop `start()` runs, with one `RunnerDaemon`
  across connections (`daemon.serve(session)` per connection). The
  one-shot `RunnerDaemon.run(session)` still works for outside callers.

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
