import yaml
import os

from pydoc_markdown import PydocMarkdown


if __name__ == "__main__":
    config = yaml.safe_load(open(".pydocs"))

    pydoc = PydocMarkdown()

    pydoc.load_config(config)
    pydoc.load_modules()
    pydoc.process()
    pydoc.render()

    os.remove(f"build/docs/mkdocs.yml")
