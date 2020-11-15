from inspect import getmembers, isclass
from typing import List


def is_class_of(cls: type, class_or_tuple) -> bool:
    return not (isclass(cls) and issubclass(cls, class_or_tuple))


def get_annotations(obj: object):
    """ Returns the annotations of a class """
    members = getmembers(obj)
    for _, v in enumerate(members):
        if v[0] == "__annotations__":
            return v[1]
    return None


# https://stackoverflow.com/questions/20656135/python-deep-merge-dictionary-data
def deep_merge(source, destination):
    """
    run me with nosetests --with-doctest file.py

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value

    return destination


def pick(dic: dict, keys: List[str]):
    return {key: dic[key] for key in keys}
