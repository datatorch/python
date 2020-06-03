import click

from datatorch.core import settings, BASE_URL


@click.command()
@click.argument('key', nargs=-1)
@click.option('--host', default=BASE_URL, help='Login to a specific instance of DataTorch')
@click.option('--no-web', is_flag=True, help='Disable opening webbrowser to access token link')
@click.option('--globally', is_flag=True, help='Save settings globally')
def login(key: str, host: str, no_web, globally):
    global settings

    if not no_web:
        import webbrowser
        webbrowser.open('{}/settings/access-tokens'.format(host))

    settings.set('API_KEY', '123123', globally=globally)
    settings.set('BASE_URL', host, globally=globally)
