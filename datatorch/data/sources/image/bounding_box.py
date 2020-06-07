class BoundingBox(object):
    @classmethod
    def create(cls, x: float, y: float, width: float, height: float):
        return cls(x=x, y=y, width=width, height=height)
