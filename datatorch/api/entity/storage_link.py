from typing import ClassVar

from .base import BaseEntity


class StorageLink(BaseEntity):

    id: ClassVar[str]
    project_id: ClassVar[str]
    name: ClassVar[str]
    type: ClassVar[str]
