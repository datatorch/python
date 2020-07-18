import click

from datatorch.api import ApiClient


@click.command(help="Uploads a flow yaml/json to webserver.")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
def upload(path):
    query = """
    mutation CreateFlow($str: String!) {
        createFlow(yaml: $str) {
            id
            name
        }
    }
    """
    with open(path) as fp:
        config = fp.read()

    api = ApiClient()
    results = api.execute(query, params={"str": config})
    flow = results.get("createFlow")

    click.echo(click.style("Flow successfully created!", bold=True))
    click.echo(f"ID: {flow.get('id')}")
    click.echo(f"Name: {flow.get('name')}")
