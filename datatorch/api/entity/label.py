from typing import ClassVar

from .base import BaseEntity


__all__ = "Label"


class Label(BaseEntity):

    id: ClassVar[str]
    name: ClassVar[str]
    color: ClassVar[str]
    custom_id: ClassVar[str]
    metadata: ClassVar[dict]
    parentId: ClassVar[dict]
