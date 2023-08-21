import numpy as np

from typing import List, Optional
from imantics import Polygons, Mask
import shapely.ops
from shapely import geometry

from .typings import Segment
from ..source import Source
from ....scripts.utils.simplify import simplify_points
from ....entity.annotation import Annotation
from datatorch.api import ApiClient


__all__ = "Segmentations"


class Segmentations(Source):
    id: str
    type: str = "PaperSegmentations"
    path_data: List[Segment]

    def __init__(self, path_data: Optional[List[Segment]] = None):
        super().__init__()
        self.path_data = path_data or []

    def from_mask(self, mask: np.array, simplify: int = 0):
        # convert mask to polygons
        polygons = Mask(mask).polygons().points
        # TODO: handle shifted polygons in cropped case
        polygons = [polygon.tolist() for polygon in polygons]

        # polygons -> path_data
        # simplify
        self.path_data = polygons
        if simplify:
            self.path_data = [
                simplify_points(polygon, tolerance=simplify, highestQuality=False)
                for polygon in polygons
            ]

        # filter polygons
        self.path_data = list(filter(lambda x: len(x) > 2, self.path_data))

    def combine_segmentations(self, annotation):
        if len(self.path_data) == 0:
            raise ValueError("No path data to combine")

        self.annotation_id = annotation.id
        existing_segmentation = next(
            x
            for x in annotation.get("sources")
            if x.get("type") == "PaperSegmentations"
        )
        poly_1 = [geometry.Polygon(points) for points in self.path_data]
        poly_2 = [geometry.Polygon(points) for points in existing_segmentation]

        multi = shapely.ops.unary_union(poly_1 + poly_2)

        if isinstance(multi, geometry.Polygon):
            self.path_data.append(list(multi.exterior.coords[:-1]))

        if isinstance(multi, geometry.MultiPolygon):
            for polygon in multi:
                self.path_data.append(list(polygon.exterior.coords[:-1]))

        self.save(ApiClient())
        print(
            f"Updated segmentation for annotation {annotation.id}",
            flush=True,
        )

    def create_new_segmentation(self, label_id: str, file_id: str):
        print("Creating new annotation")
        new_annotation = Annotation()
        new_annotation.label_id = label_id
        new_annotation.file_id = file_id
        new_annotation.create(ApiClient())
        annotation_id = new_annotation.id

        self.annotation_id = annotation_id
        self.create(ApiClient())
        print("Segmentation created with annotation", annotation_id, flush=True)

    def create_segmentation_from_mask(
        self,
        mask: np.array,
        simplify: int = 0,
        annotation=None,
        label_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ):
        if annotation is None and (label_id is None or file_id is None):
            raise ValueError("Either annotation or label_id and file_id must be set")

        self.from_mask(mask, simplify=simplify)
        if annotation:
            self.combine_segmentations(annotation)
        else:
            self.create_new_segmentation(label_id, file_id)

    def to_mask(self) -> np.array:
        raise NotImplementedError("to_mask not implemented")
