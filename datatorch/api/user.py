from typing import ClassVar
from .base import Entity


class User(Entity):
    """ Projects contain datasets, files and annotations. """

    id: ClassVar[str]
    name: ClassVar[str]
    login: ClassVar[str]
    email: ClassVar[str]
    company: ClassVar[str]
    location: ClassVar[str]
    website_url: ClassVar[str]
    role: ClassVar[str]
