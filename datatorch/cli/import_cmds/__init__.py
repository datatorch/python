import click

from .coco import coco_cmd
from .binmask import binmask_cmd

@click.group("import", help="Commands for importing annotations.")
def import_cmd():
    pass


import_cmd.add_command(coco_cmd)
import_cmd.add_command(binmask_cmd)