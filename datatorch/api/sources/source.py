from ..base import BaseEntity


class Source(BaseEntity):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = self.__class__.type
