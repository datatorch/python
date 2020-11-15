from typing import Any, Callable, Generic, TypeVar, Union


T = TypeVar("T")
R = TypeVar("R")


class HashTable(Generic[T, R]):
    def __init__(self, hash_func: Callable[[T], str]):
        self.hash = hash_func
        self.table = {}

    def set(self, input: T, value: R):
        result = self.hash(input)
        self.table[result] = value

    def has(self, input: T):
        result = self.hash(input)
        return self.table.get(result) is not None

    def get(self, input: T, default: Any = None) -> Union[R, None]:
        result = self.hash(input)
        return self.table.get(result, default)
