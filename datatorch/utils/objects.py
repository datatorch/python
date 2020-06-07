from inspect import getmembers


def get_annotations(obj: object):
    """ Returns the annotations of a class """
    members = getmembers(obj)
    for _, v in enumerate(members):
        if v[0] == "__annotations__":
            return v[1]
    return None
