import click

from .coco import coco_cmd


@click.group("import", help="Commands for importing annotations.")
def import_cmd():
    pass


import_cmd.add_command(coco_cmd)
