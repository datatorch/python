from ..source import Source

from .typings import Point2D


__all__ = "BoundingBox"


class BoundingBox(Source):
    """ Bounding Box an enclosing retangular box for a image marking """

    id: str
    type: str = "PaperBox"
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def xywh(cls, x, y, width, height):
        return cls(dict(x=x, y=y, width=width, height=height))

    @property
    def top_left(self) -> Point2D:
        """ Top-left point of the box """
        return (self.x, self.y)

    @property
    def bottom_right(self) -> Point2D:
        return (self.x + self.width, self.y + self.height)

    @property
    def size(self) -> float:
        return self.width * self.height
