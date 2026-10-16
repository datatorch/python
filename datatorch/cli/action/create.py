import os
import click
import yaml
import json as jsonlib

# What a local action's run.py starts as: the image comes in, a result
# goes out, and the model goes in the middle.
MODEL_SCRIPT = """import datatorch

image_path = datatorch.get_input("imagePath")

# Load your model and run it on image_path here. Return what it found as
# a list of shapes in pixel coordinates; each one needs a label name and
# a bbox [x, y, width, height], a polygon [[x, y], ...] or points
# [[x, y], ...]. DataTorch puts them on the file when the run completes.
# Anything your model needs must be installed in the Python this runner
# runs with.
annotations = [
    {"label": "example", "bbox": [10, 10, 100, 80], "score": 0.9},
]

datatorch.set_output("annotations", annotations)
"""


@click.command(
    help="Creates a basic hello world action in the current folder, or, with "
    "--local, in this runner's own actions folder so a pipeline can run it as "
    "local/<name>@<tag> without putting the code anywhere else."
)
@click.option(
    "-l",
    "--local",
    "local_name",
    type=str,
    default=None,
    metavar="NAME",
    help="Create it under the runner's actions/local/NAME/TAG folder (lowercase, "
    "digits, - and _). The runner reports it to DataTorch within a minute.",
)
@click.option(
    "-t",
    "--tag",
    type=str,
    default="v1",
    show_default=True,
    help="With --local: the tag folder. Pipelines pin it as local/NAME@TAG.",
)
@click.option(
    "-n",
    "--name",
    type=str,
    default="Hello World",
    help="Name of action to be created.",
)
@click.option(
    "-d",
    "--description",
    type=str,
    default="Action created using CI template.",
    help="Description of action to be created.",
)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help="Use JSON action instead of YAML. JSON format supports schemas for better typing.",
)
def create(name, description, json, local_name, tag):
    target = "."
    if local_name is not None:
        from datatorch.runner.directory import RunnerDirectory, runner_directory

        if not RunnerDirectory.LOCAL_ACTION_NAME.match(local_name):
            raise click.BadParameter(
                "use lowercase letters, digits, - and _", param_hint="--local"
            )
        if not RunnerDirectory.LOCAL_ACTION_TAG.match(tag):
            raise click.BadParameter("not a tag folder name", param_hint="--tag")
        target = os.path.join(runner_directory.local_actions_dir, local_name, tag)
        os.makedirs(target, exist_ok=True)
        if name == "Hello World":
            name = local_name
    if local_name is not None:
        # A local action is almost always someone's own model: start it
        # as one. The runner hands over the image's path; run.py returns
        # a result. Mirrors the in-browser editor's scaffold.
        config = {
            "$schema": "http://datatorch.io/schema/action.v1.json",
            "name": name,
            "description": (
                description
                if description != "Action created using CI template."
                else "Runs my model on one image."
            ),
            "inputs": {
                "imagePath": {
                    "type": "string",
                    "required": True,
                    "description": "Path of the image on disk",
                }
            },
            "outputs": {
                "annotations": {
                    "description": "Shapes found in the image; DataTorch puts them on the file"
                }
            },
            "runs": {"using": "python", "main": "run.py"},
        }
        with open(os.path.join(target, "run.py"), "w") as script:
            script.write(MODEL_SCRIPT)
        with open(os.path.join(target, "requirements.txt"), "w") as reqs:
            reqs.write(
                "# One package per line, as for pip. The runner installs them\n"
                "# into this action's own environment on first run.\n"
            )
    else:
        config = {
            "$schema": "http://datatorch.io/schema/action.v1.json",
            "name": name,
            "description": description,
            "inputs": {
                "example": {
                    "type": "string",
                    "description": "Input string that will get printed to console.",
                    "default": "Default Example",
                }
            },
            "outputs": {},
            # Inputs reach shell commands as $INPUT_<NAME> environment variables;
            # interpolating ${{ input.* }} into a command raises InputInjectionError.
            "runs": {"using": "cmd", "command": 'echo "$INPUT_EXAMPLE"'},
        }
    if json:
        with open(os.path.join(target, "action-datatorch.json"), "w") as outfile:
            jsonlib.dump(config, outfile, indent=2, sort_keys=True)
    else:
        with open(os.path.join(target, "action-datatorch.yaml"), "w") as outfile:
            yaml.dump(config, outfile, default_flow_style=False)
    if local_name is not None:
        click.echo(f"Created {os.path.abspath(target)}")
        click.echo(
            f"Reference it from a pipeline step as: action: local/{local_name}@{tag}"
        )
