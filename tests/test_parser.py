import json
import unittest
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol, runtime_checkable

import rtoml

from classconf import (
    ConfigParser,
    InvalidConfigClassError,
    MultipleTopLevelConfigError,
    configclass,
)
from classconf.format import JSONFormat, TOMLFormat


class TestConfigParser(unittest.TestCase):
    def test_separate_classes_json_format(self) -> None:
        @configclass(name="alpha")
        class AlphaConfig:
            label: str = "alpha"

        @configclass(name="beta")
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

    def test_union_type_field(self) -> None:
        @configclass(name="alpha")
        class AlphaConfig:
            label: str | None = None

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                AlphaConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            expected = json.dumps({"alpha": {"label": None}}, indent=2)
            self.assertEqual(config_path.read_text(), expected)

            alpha = parser.get(AlphaConfig)
            self.assertEqual(alpha.label, None)

    def test_top_level_with_nested_types(self) -> None:
        @configclass
        class PathsConfig:
            output_dir: Path = Path("./out")

        @configclass
        class FlagsConfig:
            retries: int = 3
            verbose: bool = False

        @configclass(top_level=True)
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
        class MainConfig:
            title: str = "main"
            enabled: bool = True

        @configclass
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
        class NamedNested:
            value: str = "value"

        @configclass(top_level=True)
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
        class DefaultNested:
            value: str = "value"

        @configclass(top_level=True)
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

    def test_deserializers_without_parser_json(self) -> None:
        def deserialize_num(value: str, **_: Any) -> int:
            return int(value.rstrip("x"))

        @configclass(
            name="metrics",
            field_deserialzers={"count": deserialize_num},
        )
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

    def test_deserializers_without_parser_toml(self) -> None:
        def deserialize_num(value: str, **_: Any) -> int:
            return int(value.rstrip("x"))

        @configclass(
            name="metrics",
            field_deserialzers={"count": deserialize_num},
        )
        class MetricsConfig:
            count: int

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(rtoml.dumps({"metrics": {"count": "8x"}}))
            parser = ConfigParser(
                config_path,
                MetricsConfig,
                format=TOMLFormat(),
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

    def test_default_format_is_toml(self) -> None:
        @configclass(top_level=True)
        class DefaultFormatConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            parser = ConfigParser(config_path, DefaultFormatConfig, create_noexist=True)

            self.assertIsInstance(parser._format, TOMLFormat)
            self.assertTrue(config_path.exists())

    def test_missing_file_raises(self) -> None:
        @configclass(top_level=True)
        class MissingFileConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                ConfigParser(config_path, MissingFileConfig, format=JSONFormat())

    def test_invalid_config_class_rejected(self) -> None:
        @dataclass
        class InvalidConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with self.assertRaises(InvalidConfigClassError):
                ConfigParser(
                    config_path, InvalidConfig, format=JSONFormat(), create_noexist=True
                )

    def test_multiple_top_level_rejected(self) -> None:
        @configclass(top_level=True)
        class TopOne:
            value: int = 1

        @configclass(top_level=True)
        class TopTwo:
            value: int = 2

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with self.assertRaises(MultipleTopLevelConfigError):
                ConfigParser(
                    config_path,
                    TopOne,
                    TopTwo,
                    format=JSONFormat(),
                    create_noexist=True,
                )

    def test_missing_key_raises(self) -> None:
        @configclass(name="app")
        class RequiredConfig:
            count: int
            label: str

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps({"app": {"count": 1}}))
            parser = ConfigParser(
                config_path,
                RequiredConfig,
                format=JSONFormat(),
                create_noexist=False,
            )

            with self.assertRaises(KeyError):
                parser.get(RequiredConfig)

    def test_add_includes_new_configs(self) -> None:
        @configclass(name="alpha")
        class AlphaConfig:
            value: int

        @configclass(name="beta")
        class BetaConfig:
            label: str

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps({"alpha": {"value": 1}, "beta": {"label": "ok"}})
            )
            parser = ConfigParser(
                config_path,
                AlphaConfig,
                format=JSONFormat(),
                create_noexist=False,
            )

            parser.add(BetaConfig)
            beta = parser.get(BetaConfig)
            self.assertEqual(beta.label, "ok")

    def test_get_missing_config_class_raises(self) -> None:
        @configclass(name="alpha")
        class AlphaConfig:
            value: int = 1

        @configclass(name="beta")
        class BetaConfig:
            value: int = 2

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            parser = ConfigParser(
                config_path,
                AlphaConfig,
                format=JSONFormat(),
                create_noexist=True,
            )

            with self.assertRaises(ValueError):
                parser.get(BetaConfig)

    def test_missing_section_raises(self) -> None:
        @configclass(name="alpha")
        class AlphaConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(json.dumps({"other": {"value": 1}}))
            parser = ConfigParser(
                config_path,
                AlphaConfig,
                format=JSONFormat(),
                create_noexist=False,
            )

            with self.assertRaises(KeyError):
                parser.get(AlphaConfig)

    def test_generate_config_writes_instances(self) -> None:
        def serialize_count(value: int) -> str:
            return f"{value}x"

        @configclass(
            name="metrics",
            field_name_mappings={"count": "count_value"},
            field_serializers={"count": serialize_count},
        )
        class MetricsConfig:
            count: int = 7

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            ConfigParser.generate_config(
                config_path,
                MetricsConfig(count=9),
                format=JSONFormat(),
                override_existing=False,
            )

            self.assertEqual(
                json.loads(config_path.read_text()),
                {"metrics": {"count_value": "9x"}},
            )

    def test_generate_config_top_level(self) -> None:
        @configclass(top_level=True)
        class TopConfig:
            name: str = "demo"

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            ConfigParser.generate_config(
                config_path,
                TopConfig(name="prod"),
                format=JSONFormat(),
            )

            self.assertEqual(json.loads(config_path.read_text()), {"name": "prod"})

    def test_generate_config_requires_override(self) -> None:
        @configclass(top_level=True)
        class TopConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text("{}")

            with self.assertRaises(FileExistsError):
                ConfigParser.generate_config(
                    config_path,
                    TopConfig(),
                    format=JSONFormat(),
                    override_existing=False,
                )

            ConfigParser.generate_config(
                config_path,
                TopConfig(value=2),
                format=JSONFormat(),
                override_existing=True,
            )

            self.assertEqual(json.loads(config_path.read_text()), {"value": 2})

    def test_generate_config_duplicate_instances(self) -> None:
        @configclass(top_level=True)
        class TopConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with self.assertRaises(ValueError):
                ConfigParser.generate_config(
                    config_path,
                    TopConfig(),
                    TopConfig(value=2),
                    format=JSONFormat(),
                )

    def test_generate_config_invalid_instance(self) -> None:
        @dataclass
        class InvalidConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with self.assertRaises(InvalidConfigClassError):
                ConfigParser.generate_config(
                    config_path,
                    InvalidConfig(),
                    format=JSONFormat(),
                )

    def test_generate_config_defaults_to_toml(self) -> None:
        @configclass(top_level=True)
        class TopConfig:
            value: int = 1

        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            ConfigParser.generate_config(config_path, TopConfig(value=3))

            self.assertEqual(rtoml.load(config_path), {"value": 3})


if __name__ == "__main__":
    unittest.main()
