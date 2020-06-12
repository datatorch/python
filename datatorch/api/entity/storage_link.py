from typing import ClassVar

from .base import BaseEntity


__all__ = "StorageLink"


class StorageLink(BaseEntity):

    id: ClassVar[str]
    project_id: ClassVar[str]
    name: ClassVar[str]
    type: ClassVar[str]
