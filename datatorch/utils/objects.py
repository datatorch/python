from inspect import getmembers, isclass


def is_class_of(cls: type, class_or_tuple) -> bool:
    return not (isclass(cls) and issubclass(cls, class_or_tuple))


def get_annotations(obj: object):
    """ Returns the annotations of a class """
    members = getmembers(obj)
    for _, v in enumerate(members):
        if v[0] == "__annotations__":
            return v[1]
    return None
