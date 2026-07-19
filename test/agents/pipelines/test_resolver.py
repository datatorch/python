import unittest

from datatorch.agent.pipelines.resolver import (
    UnresolvedReferenceError,
    resolve_step_input,
)

OUTPUTS = {
    "Count": {"total": 42, "meta": {"kind": "files"}},
    "Fetch": {"url": "https://x.io", "ok": True},
}
TRIGGER = {"userId": "u1", "input": {"threshold": 5}}


def resolve(inputs):
    return resolve_step_input(inputs, OUTPUTS, TRIGGER)


class TestResolveStepInput(unittest.TestCase):
    """Mirrors the server's StepInputResolver.test.ts fixtures."""

    def test_whole_string_ref_raw_number(self):
        value, unresolved = resolve({"total": "${{ steps.Count.output.total }}"})
        self.assertEqual(value, {"total": 42})
        self.assertEqual(unresolved, [])

    def test_whole_string_ref_raw_object(self):
        value, _ = resolve({"meta": "${{ steps.Count.output.meta }}"})
        self.assertEqual(value, {"meta": {"kind": "files"}})

    def test_outputs_alias(self):
        value, _ = resolve({"total": "${{ steps.Count.outputs.total }}"})
        self.assertEqual(value, {"total": 42})

    def test_embedded_refs_interpolate_as_strings(self):
        value, unresolved = resolve(
            {
                "msg": "found ${{ steps.Count.output.total }} "
                "at ${{ steps.Fetch.output.url }}"
            }
        )
        self.assertEqual(value, {"msg": "found 42 at https://x.io"})
        self.assertEqual(unresolved, [])

    def test_embedded_object_refs_json_stringify(self):
        value, _ = resolve({"msg": "meta=${{ steps.Count.output.meta }}"})
        self.assertEqual(value, {"msg": 'meta={"kind": "files"}'})

    def test_embedded_bool_matches_server_casing(self):
        value, _ = resolve({"msg": "ok=${{ steps.Fetch.output.ok }}"})
        self.assertEqual(value, {"msg": "ok=true"})

    def test_trigger_input_refs(self):
        value, unresolved = resolve(
            {"who": "${{ input.userId }}", "t": "${{ inputs.input }}"}
        )
        self.assertEqual(value, {"who": "u1", "t": {"threshold": 5}})
        self.assertEqual(unresolved, [])

    def test_recurses_into_arrays_and_objects(self):
        value, _ = resolve(
            {
                "list": ["${{ steps.Count.output.total }}", "x"],
                "nested": {"deep": {"v": "${{ steps.Fetch.output.ok }}"}},
            }
        )
        self.assertEqual(value, {"list": [42, "x"], "nested": {"deep": {"v": True}}})

    def test_collects_unresolved_and_leaves_untouched(self):
        value, unresolved = resolve(
            {
                "typo": "${{ steps.Cont.output.total }}",
                "missing_key": "${{ steps.Count.output.nope }}",
                "missing_input": "${{ input.nope }}",
            }
        )
        self.assertEqual(value["typo"], "${{ steps.Cont.output.total }}")
        self.assertEqual(len(unresolved), 3)

    def test_machine_local_namespaces_pass_through(self):
        value, unresolved = resolve(
            {"dir": "${{ agent.directory }}/x", "m": "${{ machine.name }}"}
        )
        self.assertEqual(
            value, {"dir": "${{ agent.directory }}/x", "m": "${{ machine.name }}"}
        )
        self.assertEqual(unresolved, [])

    def test_non_string_scalars_and_none(self):
        value, unresolved = resolve({"n": 7, "b": False, "nil": None})
        self.assertEqual(value, {"n": 7, "b": False, "nil": None})
        self.assertEqual(unresolved, [])

    def test_step_names_with_spaces(self):
        value, _ = resolve_step_input(
            {"t": "${{ steps.Count Files.output.total }}"},
            {"Count Files": {"total": 3}},
        )
        self.assertEqual(value, {"t": 3})

    def test_error_message_lists_refs(self):
        err = UnresolvedReferenceError(["${{ steps.X.output.y }}"])
        self.assertIn("${{ steps.X.output.y }}", str(err))

    def test_job_output_ref_resolves_when_supplied(self):
        # Parity with the server: whole-string -> raw value, embedded ->
        # stringified. Job outputs come in via the 4th arg (server-only path;
        # local mode passes none — see below).
        value, unresolved = resolve_step_input(
            {
                "raw": "${{ jobs.build.outputs.artifact }}",
                "msg": "built ${{ jobs.build.outputs.artifact }}",
            },
            {},
            {},
            {"build": {"artifact": "app.tar"}},
        )
        self.assertEqual(value, {"raw": "app.tar", "msg": "built app.tar"})
        self.assertEqual(unresolved, [])

    def test_job_outputs_alias(self):
        value, _ = resolve_step_input(
            {"x": "${{ jobs.build.output.n }}"}, {}, {}, {"build": {"n": 3}}
        )
        self.assertEqual(value, {"x": 3})

    def test_job_output_unresolvable_in_local_mode(self):
        # Local mode supplies no job outputs (single-job execution), so a
        # jobs.* reference is a strict miss rather than a silent pass-through.
        value, unresolved = resolve({"x": "${{ jobs.build.outputs.artifact }}"})
        self.assertEqual(value["x"], "${{ jobs.build.outputs.artifact }}")
        self.assertEqual(unresolved, ["${{ jobs.build.outputs.artifact }}"])
