import unittest
from datatorch.utils import get_annotations


class ExampleClass(object):
    var1: str
    var2: int
    var3: float


class TestClassAnnotation(unittest.TestCase):
    def test_returns_classes(self):
        result = ["var1", "var2", "var3"]
        output = get_annotations(ExampleClass)
        self.assertCountEqual(result, output)
