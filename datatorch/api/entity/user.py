from typing import ClassVar
from .base import BaseEntity


__all__ = "User"


class User(BaseEntity):
    """ Projects contain datasets, files and annotations. """

    id: ClassVar[str]
    name: ClassVar[str]
    login: ClassVar[str]
    email: ClassVar[str]
    display_name: ClassVar[str]
    company: ClassVar[str]
    location: ClassVar[str]
    website_url: ClassVar[str]
    role: ClassVar[str]
