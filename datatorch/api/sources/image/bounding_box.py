
from typing import Tuple, ClassVar
from ..source import Source

from .typings import Point2D


class BoundingBox(Source):
    """ Bounding Box an enclosing retangular box for a image marking """

    id: str
    type: str = 'PaperBox'
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def create(cls, x, y, width, height):
        return cls(dict(x=x, y=y, width=width, height=height))

    @property
    def point(self) -> Point2D:
        """ Top-left point of the box """
        return [x, y]

    @property
    def size(self) -> float:
        return self.width * self.height
