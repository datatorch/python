import unittest

from datatorch.runner.pipelines.template import (
    InputInjectionError,
    Variables,
    global_variables,
)


class TestVariables(unittest.TestCase):
    """Protocol v2: only machine-local and action-local namespaces render."""

    def test_machine_local_namespaces_render(self):
        v = Variables()
        self.assertEqual(
            v.render("${{ machine.os }}"), global_variables["machine"]["os"]
        )
        self.assertEqual(
            v.render("${{ directory.agent }}"),
            global_variables["directory"]["agent"],
        )

    def test_step_inputs_render_via_input_namespace(self):
        v = Variables()
        v.add_input("total", 42)
        self.assertEqual(v.render("${{ input.total }}"), "42")

    def test_variable_is_an_alias_of_input(self):
        v = Variables()
        v.add_input("total", 42)
        self.assertEqual(v.render("${{ variable.total }}"), "42")
        self.assertEqual(v.inputs, {"total": 42})

    def test_string_inputs_render_machine_local_refs(self):
        v = Variables()
        v.add_input("path", "${{ directory.temp }}/x")
        self.assertEqual(v.inputs["path"], global_variables["directory"]["temp"] + "/x")

    def test_server_namespaces_pass_through_unchanged(self):
        # job/pipeline/trigger/event/steps/inputs/secrets are server
        # concepts: the server resolves them before dispatch, so any such
        # text still in an input is data the runner did not author. It is
        # left exactly as written: not rendered, not emptied, no error.
        # (`run` is runner-owned since 0.8.1; see test_run_identity.)
        v = Variables()
        for template in (
            "${{ job.id }}",
            "${{ pipeline.id }}",
            "${{ trigger.type }}",
            "${{ event.userId }}",
            "${{ steps.fetch.output.body }}",
            "${{ inputs.message }}",
            "${{ jobs.build.output.path }}",
            "${{ secrets.NAME }}",
            "${{ nobody.knows }}",
            "${{ unknown }}",
        ):
            self.assertEqual(v.render(template), template)

    def test_foreign_text_passes_through_while_own_refs_render(self):
        v = Variables()
        rendered = v.render(
            'error: "${{ steps.fetch.output.body }}" key=${{ secrets.NAME }} '
            "on ${{ machine.name }} in ${{directory.temp}}"
        )
        self.assertEqual(
            rendered,
            'error: "${{ steps.fetch.output.body }}" key=${{ secrets.NAME }} '
            "on "
            + global_variables["machine"]["name"]
            + " in "
            + global_variables["directory"]["temp"],
        )

    def test_string_input_carrying_server_refs_is_inert(self):
        # The watchdog-sense case: a JSON snapshot of older failure
        # messages, inlined into a `message` input, quoted `${{ steps... }}`.
        snapshot = (
            '{"errors": ["Step failed: ${{ steps.fetch.output.body }}", '
            '"missing ${{ secrets.NAME }}"], "host": "${{ machine.name }}"}'
        )
        v = Variables()
        v.add_input("message", snapshot)
        self.assertEqual(
            v.inputs["message"],
            snapshot.replace(
                "${{ machine.name }}", global_variables["machine"]["name"]
            ),
        )

    def test_nested_object_and_array_inputs_pass_through(self):
        snapshot = {
            "errors": ["${{ steps.fetch.output.body }}", {"k": "${{ secrets.NAME }}"}],
            "host": "${{ machine.name }}",
        }
        v = Variables()
        v.add_input("snapshot", snapshot)
        v.add_input("list", ["${{ steps.a.output.b }}", "${{ job.id }}"])
        self.assertEqual(v.inputs["snapshot"], snapshot)
        self.assertEqual(v.inputs["list"], ["${{ steps.a.output.b }}", "${{ job.id }}"])

    def test_expression_mixing_foreign_and_own_names_is_data(self):
        v = Variables()
        template = "${{ machine.name ~ steps.x.output.y }}"
        self.assertEqual(v.render(template), template)

    def test_malformed_and_unclosed_expressions_never_raise(self):
        v = Variables()
        for text in (
            "${{ }}",
            "${{ not valid jinja ( }}",
            "${{ steps.x",
            "${% if steps.x %}",
        ):
            self.assertEqual(v.render(text), text)

    def test_rendering_is_idempotent_for_foreign_text(self):
        # Inputs are rendered twice on the way to an action (the step seeds
        # them, the action's type-cast pass re-adds strings); the second
        # pass must not change what the first one kept.
        v = Variables()
        text = "${{ steps.fetch.output.body }} on ${{ machine.name }}"
        once = v.render(text)
        self.assertEqual(v.render(once), once)

    def test_run_namespace_still_renders_in_inputs(self):
        # `run` is the runner's own since 0.8.1 (set by set_step), so a
        # string input may read it, next to text it must not touch.
        v = Variables()
        v.set("run", {"id": "run-1", "projectId": "proj-1"})
        v.add_input("note", "${{ run.id }} saw ${{ steps.fetch.output.body }}")
        self.assertEqual(v.inputs["note"], "run-1 saw ${{ steps.fetch.output.body }}")

    def test_own_namespace_behaviour_is_unchanged(self):
        v = Variables()
        v.add_input("total", 42)
        self.assertEqual(v.render("${{ input.total }}"), "42")
        self.assertEqual(v.render("${{ 'literal' }}"), "literal")
        self.assertEqual(v.render("no refs here"), "no refs here")
        self.assertIsNone(v.render(None))

    def test_inputs_are_scoped_per_instance(self):
        a = Variables()
        a.add_input("x", 1)
        b = Variables()
        self.assertEqual(b.inputs, {})


class TestCommandInjectionPolicy(unittest.TestCase):
    """Shell/cmd commands must read inputs from $INPUT_<NAME> env vars, not
    interpolate ${{ input.* }} (DataTorch injection policy)."""

    def test_render_command_allows_machine_local_refs(self):
        v = Variables()
        self.assertEqual(
            v.render_command("echo ${{ machine.os }}"),
            "echo " + global_variables["machine"]["os"],
        )

    def test_render_command_forbids_input_ref(self):
        v = Variables()
        v.add_input("message", "hello")
        with self.assertRaises(InputInjectionError):
            v.render_command("echo ${{ input.message }}")

    def test_render_command_forbids_variable_alias(self):
        v = Variables()
        v.add_input("message", "hello")
        with self.assertRaises(InputInjectionError):
            v.render_command("echo ${{ variable.message }}")

    def test_render_command_forbids_input_in_block(self):
        v = Variables()
        v.add_input("items", [1, 2])
        with self.assertRaises(InputInjectionError):
            v.render_command("${% for i in input.items %}x${% endfor %}")

    def test_render_command_passes_through_shell_env_syntax(self):
        # $INPUT_MESSAGE is a shell variable, not a template ref — untouched.
        v = Variables()
        v.add_input("message", "hello")
        self.assertEqual(
            v.render_command('echo "$INPUT_MESSAGE"'), 'echo "$INPUT_MESSAGE"'
        )

    def test_render_command_none_passes_through(self):
        self.assertIsNone(Variables().render_command(None))

    def test_env_inputs_key_and_scalar_stringify(self):
        v = Variables()
        v.add_input("message", "hi")
        v.add_input("max-count", 5)
        env = v.env_inputs()
        self.assertEqual(env["INPUT_MESSAGE"], "hi")
        # non-identifier chars in the key normalize to underscores
        self.assertEqual(env["INPUT_MAX_COUNT"], "5")

    def test_env_inputs_bool_is_shell_friendly(self):
        v = Variables()
        v.add_input("enabled", True)
        v.add_input("disabled", False)
        env = v.env_inputs()
        self.assertEqual(env["INPUT_ENABLED"], "true")
        self.assertEqual(env["INPUT_DISABLED"], "false")

    def test_env_inputs_objects_and_arrays_json_encode(self):
        v = Variables()
        v.add_input("obj", {"a": 1})
        v.add_input("arr", [1, 2])
        env = v.env_inputs()
        self.assertEqual(env["INPUT_OBJ"], '{"a": 1}')
        self.assertEqual(env["INPUT_ARR"], "[1, 2]")

    def test_env_inputs_none_is_empty_string(self):
        v = Variables()
        v.add_input("missing", None)
        self.assertEqual(v.env_inputs()["INPUT_MISSING"], "")

    def test_malicious_input_value_never_reaches_command(self):
        # The whole point: a `; rm -rf ~` input value is inert — it lands
        # in an env var, and the command that references it does not
        # interpolate it as code.
        v = Variables()
        v.add_input("name", "; rm -rf ~")
        rendered = v.render_command('echo "$INPUT_NAME"')
        self.assertNotIn("rm -rf", rendered)
        self.assertEqual(v.env_inputs()["INPUT_NAME"], "; rm -rf ~")
