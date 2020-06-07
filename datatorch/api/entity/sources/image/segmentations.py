import numpy as np

from typing import List, Tuple

from .typings import Segment
from ..source import Source


class Segmentations(Source):

    id: str
    type: str = "PaperSegmentations"
    path_data: List[Segment]

    def from_mask(self, mask: np.array):
        pass

    def to_mask(self) -> np.array:
        pass
