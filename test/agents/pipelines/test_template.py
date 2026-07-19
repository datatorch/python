import unittest

from datatorch.agent.pipelines.template import (
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
        self.assertEqual(
            v.inputs["path"], global_variables["directory"]["temp"] + "/x"
        )

    def test_retired_namespaces_raise(self):
        # job/run/pipeline/trigger/event are server-side concepts now; the
        # agent context no longer carries them, so referencing one fails
        # the step loudly instead of silently rendering an empty string.
        from jinja2.exceptions import UndefinedError

        v = Variables()
        for template in ("${{ run.id }}", "${{ trigger.type }}", "${{ event.userId }}"):
            with self.assertRaises(UndefinedError):
                v.render(template)

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
