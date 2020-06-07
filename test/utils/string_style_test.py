import unittest
from datatorch.utils.string_style import camel_to_snake, snake_to_camel


class TestCamelToSnake(unittest.TestCase):
    def test_string(self):
        string = "camelToSnakeTest"
        result = "camel_to_snake_test"
        output = camel_to_snake(string)
        assert output == result

    def test_dict(self):
        dict_ = {
            "camelLevel1": True,
            "nestedObj": {"camelLevel2": "shouldNotBeChanged"},
        }
        result = {
            "camel_level1": True,
            "nested_obj": {"camel_level2": "shouldNotBeChanged"},
        }
        output = camel_to_snake(dict_)
        self.assertDictEqual(output, result)
