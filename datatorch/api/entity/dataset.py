from typing import ClassVar
from .base import BaseEntity


class Dataset(BaseEntity):

    id: str
    name: str
    description: str
    project_id: str
    kilobytes: int
    formatted_bytes: int
    created_at: str
    updated_at: str
