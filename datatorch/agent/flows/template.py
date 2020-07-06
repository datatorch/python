import platform

from jinja2 import Template


global_variables = {
    "machine": {
        "name": platform.machine(),
        "system": platform.system(),
        "version": platform.version(),
    },
    "python": {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
    },
}


def render(string: str, variables):
    """ Renders a templated string. """
    tp = Template(string)
    return tp.render({**global_variables, **variables})


def add_variables(dic: dict):
    """ Adds dict to local variables. These can be accessed when rendering. """
    global global_variables
    global_variables = {**global_variables, **dic}
