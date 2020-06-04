from typing import ClassVar
from .base import Entity


class Dataset(Entity):

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    project_id: ClassVar[str]
    kilobytes: ClassVar[int]
    formatted_bytes: ClassVar[int]
    is_archived: ClassVar[bool]
    created_at: ClassVar[str]
    updated_at: ClassVar[str]
