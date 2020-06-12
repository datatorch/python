from datatorch.utils import snake_to_camel


__all__ = "Where", "InvalidOperatorError"


class InvalidOperatorError(Exception):
    pass


operators = {
    "equals",
    "not_equals",
    "in",
    "gt",
    "gte",
    "lt",
    "lte" "like",
    "starts_with",
    "ends_with",
}


class Where(object):
    __slot__ = ("input",)

    def __init__(self, **kwargs):
        self.input: dict = {}

        for key, value in kwargs.items():
            if isinstance(value, Where):
                self.input[key] = value.input
                continue
            split = key.split("__")
            if len(split) == 1:
                split.append("equals")
            field, operation = split
            self._set(field, operation, value)

    def add(self, field, where):
        self.input[field] = where.input

    def _set(self, field, operation, value):
        if operation not in operators:
            raise InvalidOperatorError(f"{operation} is not a valid operator.")

        field = snake_to_camel(field)
        operation = snake_to_camel(operation)

        where = self.input
        for key in field.split("."):
            if key not in self.input:
                where[field] = {}
            where = where[field]
        where[operation] = value
        return self
