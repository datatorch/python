from typing import Type, TypeVar

T = TypeVar("T")


class Wrapper:
    """Wrapper class that provides proxy access to an instance of some
    internal instance."""

    __wraps__: Type = None
    __ignore__ = "class mro new init setattr getattr getattribute"
    __override__ = ""

    def __init__(self, obj):
        if self.__wraps__ is None:
            raise TypeError("base class Wrapper may not be instantiated")
        elif isinstance(obj, self.__wraps__):
            self._obj = obj
        else:
            raise ValueError("wrapped object must be of %s" % self.__wraps__)

    # provide proxy access to regular attributes of wrapped object
    def __getattr__(self, name):
        return getattr(self._obj, name)

    # create proxies for wrapped object's double-underscore attributes
    class __metaclass__(type):
        def __init__(cls, name, bases, dct):
            def make_proxy(name):
                def proxy(self, *args):
                    return getattr(self._obj, name)

                return proxy

            type.__init__(cls, name, bases, dct)
            if cls.__wraps__:  # type: ignore
                ignore = set("__%s__" % n for n in cls.__ignore__.split())  # type: ignore
                for name in dir(cls.__wraps__):  # type: ignore

                    if name.startswith("__"):
                        if name not in ignore and name not in dct:
                            setattr(cls, name, property(make_proxy(name)))