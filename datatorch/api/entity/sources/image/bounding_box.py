from ..source import Source

from typing import Optional
from .typings import Point2D
from datatorch.api import ApiClient
from ....entity.annotation import Annotation


__all__ = "BoundingBox"


class BoundingBox(Source):
    """Bounding Box an enclosing retangular box for a image marking"""

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
        """Top-left point of the box"""
        return (self.x, self.y)

    @property
    def bottom_right(self) -> Point2D:
        return (self.x + self.width, self.y + self.height)

    @property
    def size(self) -> float:
        return self.width * self.height

    def from_points(self, top_left: Point2D, bottom_right: Point2D):
        self.x = top_left[0]
        self.y = top_left[1]
        self.width = bottom_right[0] - top_left[0]
        self.height = bottom_right[1] - top_left[1]

    def create_new_bbox(self, label_id: str, file_id: str):
        print("Creating new annotation")
        new_annotation = Annotation()
        new_annotation.label_id = label_id
        new_annotation.file_id = file_id
        new_annotation.create(ApiClient())

        self.annotation_id = new_annotation.id
        self.create(ApiClient())
        print("BoundingBox created with annotation", new_annotation.id, flush=True)

    def combine_bbox(self, annotation):
        if self.annotation_id is None:
            raise ValueError("No annotation id set")

        self.annotation_id = annotation.id
        existing_bbox = next(
            x for x in annotation.get("sources") if x.get("type") == "PaperBox"
        )

        # Merge self and existing bbox
        top_left = (
            min(self.x, existing_bbox["x"]),
            min(self.y, existing_bbox["y"]),
        )
        bottom_right = (
            max(self.bottom_right[0], existing_bbox["x"] + existing_bbox["width"]),
            max(self.bottom_right[1], existing_bbox["y"] + existing_bbox["height"]),
        )

        self.from_points(top_left, bottom_right)

        self.save(ApiClient())
        print(
            f"Updated bounding box for annotation {annotation.id}",
            flush=True,
        )

    def create_bbox_from_points(
        self,
        top_left: Point2D,
        bottom_right: Point2D,
        annotation=None,
        label_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ):
        if annotation is None and (label_id is None or file_id is None):
            raise ValueError("Either annotation or label_id and file_id must be set")

        self.from_points(top_left, bottom_right)
        if annotation:
            self.combine_bbox(annotation)
        else:
            self.create_new_bbox(label_id, file_id)
