import click
import yaml
import json as jsonlib


@click.command(help="Creates a basic hello world action.")
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
def create(name, description, json):
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
        "runs": {"using": "cmd", "command": "echo ${{ input.example }}"},
    }
    if json:
        with open("action-datatorch.json", "w") as outfile:
            jsonlib.dump(config, outfile, indent=2, sort_keys=True)
    else:
        with open("action-datatorch.yaml", "w") as outfile:
            yaml.dump(config, outfile, default_flow_style=False)
