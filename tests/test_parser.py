import json
import unittest
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol, runtime_checkable

from dataconf import ConfigParser, configclass
from dataconf.format import JSONFormat, TOMLFormat


class TestConfigParser(unittest.TestCase):
    def test_separate_classes_json_format(self) -> None:
        @configclass(name="alpha")
        @dataclass
        class AlphaConfig:
            label: str = "alpha"

        @configclass(name="beta")
        @dataclass
        class BetaConfig:
            count: int = 5

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                AlphaConfig,
                BetaConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            expected = json.dumps(
                {"alpha": {"label": "alpha"}, "beta": {"count": 5}}, indent=2
            )
            self.assertEqual(config_path.read_text(), expected)

            alpha = parser.get(AlphaConfig)
            beta = parser.get(BetaConfig)
            self.assertEqual(alpha.label, "alpha")
            self.assertEqual(beta.count, 5)

    def test_top_level_with_nested_types(self) -> None:
        @configclass
        @dataclass
        class PathsConfig:
            output_dir: Path = Path("./out")

        @configclass
        @dataclass
        class FlagsConfig:
            retries: int = 3
            verbose: bool = False

        @configclass(top_level=True)
        @dataclass
        class AppConfig:
            name: str = "demo"
            paths: PathsConfig = field(default_factory=PathsConfig)
            flags: FlagsConfig = field(default_factory=FlagsConfig)

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                AppConfig,
                PathsConfig,
                FlagsConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            config = parser.get(AppConfig)
            self.assertEqual(config.name, "demo")
            self.assertEqual(config.flags.retries, 3)
            self.assertFalse(config.flags.verbose)
            self.assertEqual(config.paths.output_dir, Path("./out"))

    def test_top_level_with_extra_section_toml(self) -> None:
        @configclass(top_level=True)
        @dataclass
        class MainConfig:
            title: str = "main"
            enabled: bool = True

        @configclass
        @dataclass
        class ExtraConfig:
            level: int = 2

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            parser = ConfigParser(
                config_path,
                MainConfig,
                ExtraConfig,
                format=TOMLFormat(),
                create_noexist=True,
            )

            main = parser.get(MainConfig)
            extra = parser.get(ExtraConfig)
            self.assertEqual(main.title, "main")
            self.assertTrue(main.enabled)
            self.assertEqual(extra.level, 2)

    def test_nested_name_collision_allows_lookup(self) -> None:
        @configclass(name="nested")
        @dataclass
        class NamedNested:
            value: str = "value"

        @configclass(top_level=True)
        @dataclass
        class ParentConfig:
            nested: NamedNested = field(default_factory=NamedNested)

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                ParentConfig,
                NamedNested,
                format=JSONFormat(),
                create_noexist=True,
            )

            nested = parser.get(NamedNested)
            self.assertEqual(nested.value, "value")

        @configclass
        @dataclass
        class DefaultNested:
            value: str = "value"

        @configclass(top_level=True)
        @dataclass
        class ParentDefaultConfig:
            nested: DefaultNested = field(default_factory=DefaultNested)

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                ParentDefaultConfig,
                DefaultNested,
                format=JSONFormat(),
                create_noexist=True,
            )

            with self.assertRaises(KeyError):
                parser.get(DefaultNested)

    def test_missing_defaults_written_as_null(self) -> None:
        @configclass(top_level=True)
        @dataclass
        class RequiredConfig:
            count: int
            label: str

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                RequiredConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            self.assertEqual(
                json.loads(config_path.read_text()),
                {"count": None, "label": None},
            )
            config = parser.get(RequiredConfig)
            self.assertIsNone(config.count)
            self.assertIsNone(config.label)

    def test_serializers_apply_to_default_config(self) -> None:
        def serialize_count(value: int) -> str:
            return f"{value}x"

        @configclass(
            name="metrics",
            field_serializers={"count": serialize_count},
        )
        @dataclass
        class MetricsConfig:
            count: int = 3

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            ConfigParser(
                config_path,
                MetricsConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            self.assertEqual(
                json.loads(config_path.read_text()),
                {"metrics": {"count": "3x"}},
            )

    def test_deserializers_without_parser(self) -> None:
        def deserialize_num(value: str, **_: Any) -> int:
            return int(value.rstrip("x"))

        @configclass(
            name="metrics",
            field_deserialzers={"count": deserialize_num},
        )
        @dataclass
        class MetricsConfig:
            count: int

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps({"metrics": {"count": "8x"}}))
            parser = ConfigParser(
                config_path,
                MetricsConfig,
                format=JSONFormat(),
                create_noexist=False,
            )

            config = parser.get(MetricsConfig)
            self.assertEqual(config.count, 8)

    def test_deserializers_using_parser_with_serialized_field(self) -> None:
        @runtime_checkable
        class Child(Protocol):
            name: str
            size: int

        @configclass(name="child")
        @dataclass
        class ChildConfig:
            name: str = "alpha"
            size: int = 2

        def resolve_child(_: Any, parser: ConfigParser) -> ChildConfig:
            return parser.get(ChildConfig)

        def serialize_child(child: ChildConfig) -> str:
            return child.name

        @configclass(
            top_level=True,
            field_deserialzers={"child": resolve_child},
            field_serializers={"child": serialize_child},
        )
        @dataclass
        class ParentConfig:
            child: Child = field(default_factory=ChildConfig)

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                ParentConfig,
                ChildConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            parent = parser.get(ParentConfig)
            self.assertEqual(parent.child.name, "alpha")
            self.assertEqual(parent.child.size, 2)

    def test_deserializers_using_parser_with_abc_child(self) -> None:
        class Child(ABC):
            name: str
            size: int

        @configclass(name="child")
        @dataclass
        class ChildConfig(Child):
            name: str = "alpha"
            size: int = 2

        def resolve_child(_: Any, parser: ConfigParser) -> ChildConfig:
            return parser.get(ChildConfig)

        def serialize_child(child: ChildConfig) -> str:
            return child.name

        @configclass(
            top_level=True,
            field_name_mappings={"child": "child_ref"},
            field_deserialzers={"child": resolve_child},
            field_serializers={"child": serialize_child},
        )
        @dataclass
        class ParentConfig:
            child: Child = field(default_factory=ChildConfig)

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                ParentConfig,
                ChildConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            parent = parser.get(ParentConfig)
            self.assertEqual(parent.child.name, "alpha")
            self.assertEqual(parent.child.size, 2)


if __name__ == "__main__":
    unittest.main()
