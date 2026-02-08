import unittest
from dataclasses import dataclass

from dataconf import configclass

from .helpers import as_config_class


def deserialize_count(value: str) -> int:
    return int(value)


def serialize_count(value: int) -> str:
    return str(value)


class TestConfigClassDecorator(unittest.TestCase):
    def test_metadata_is_attached(self) -> None:
        @configclass(
            top_level=True,
            name="app",
            field_name_mappings={"count": "count_value"},
            field_deserialzers={"count": deserialize_count},
            field_serializers={"count": serialize_count},
        )
        @dataclass
        class ExampleConfig:
            count: int = 1

        config_class = as_config_class(ExampleConfig)
        spec = config_class.__config__

        self.assertTrue(spec.top_level)
        self.assertEqual(spec.name, "app")
        self.assertEqual(spec.field_mappings, {"count": "count_value"})
        self.assertEqual(spec.field_deserialzers, {"count": deserialize_count})
        self.assertEqual(spec.field_serializers, {"count": serialize_count})


if __name__ == "__main__":
    unittest.main()
