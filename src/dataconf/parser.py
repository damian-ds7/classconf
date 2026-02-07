from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
import types
from typing import Any, TypeVar, Union, cast, get_args, get_origin

from .format.config_format import ConfigFormat
from .format.toml_format import TOMLFormat
from .types import ConfigClass
from .utils import is_configclass_type

T = TypeVar("T")


class InvalidConfigClassError(TypeError):
    pass


class ConfigParser:
    def __init__(
        self,
        config_path: Path | str,
        *configs: type[Any],
        create_noexist: bool = False,
        format: ConfigFormat | None = None,
    ) -> None:
        if format is None:
            format = TOMLFormat()
        base_path = Path(config_path)

        if not create_noexist and not base_path.exists():
            raise FileNotFoundError("Provided config file does not exist")

        self._config_path = base_path.with_suffix(format.extension)
        self._format = format

        invalid_configs = [cls for cls in configs if not is_configclass_type(cls)]
        if invalid_configs:
            invalid_names = ", ".join(cls.__name__ for cls in invalid_configs)
            raise InvalidConfigClassError(
                f"Config classes must use @configclass: {invalid_names}"
            )

        typed_configs = cast(list[type[ConfigClass[Any]]], list(configs))
        self._configs = sorted(
            typed_configs,
            key=lambda cls: (
                0 if cls.__config__.top_level else 1,
                cls.__config__.name.casefold(),
            ),
        )
        self._config = self._read_config()

    def _read_config(self) -> dict[str, dict[str, Any]]:
        config_data = self._format.read(self._config_path)
        if config_data is None:
            return self._create_default_config()

        return config_data

    def _create_default_config(self) -> dict[str, Any]:
        config_data: dict[str, dict[str, Any]] = {}

        for config_class in self._get_root_configs():
            section_name = config_class.__config__.name
            config_class_data = ConfigParser._get_class_fields(config_class)
            config_data[section_name] = config_class_data

        self._format.write(self._config_path, config_data)

        return config_data

    @staticmethod
    def _get_class_fields(
        config_class: type[ConfigClass[Any]],
    ) -> dict[str, Any]:
        class_data: dict[str, Any] = {}

        field_mappings = {}
        field_serializers = {}
        if config_class.__config__ is not None:
            field_mappings = config_class.__config__.field_mappings
            field_serializers = config_class.__config__.field_serializers

        for field in fields(config_class):
            key = field_mappings.get(field.name, field.name)
            value = ConfigParser._get_field_default_value(field)

            value = ConfigParser._serialize_field_value(
                value, field.name, field_serializers
            )
            class_data[key] = value

        return class_data

    @staticmethod
    def _get_field_default_value(field: Any) -> Any:
        if field.default is not MISSING:
            return field.default
        elif field.default_factory is not MISSING:
            return field.default_factory()
        else:
            field_type = ConfigParser._unwrap_optional(field.type)

            if is_dataclass(field_type):
                return ConfigParser._get_class_fields(
                    cast(type[ConfigClass], field_type)
                )
            else:
                return None

    @staticmethod
    def _serialize_field_value(
        value: Any, field_name: str, field_serializers: Mapping[str, Any]
    ) -> Any:
        if value is None:
            return None
        if field_name in field_serializers:
            return field_serializers[field_name](value)
        elif isinstance(value, Path):
            return str(value)
        elif isinstance(value, ConfigClass):
            return ConfigParser._get_class_fields(type(value))
        return value

    @staticmethod
    def _unwrap_optional(field_type: Any) -> Any:
        origin = get_origin(field_type)
        if origin is Union or origin is types.UnionType:
            type_args = [t for t in get_args(field_type) if t is not type(None)]
            if type_args:
                return type_args[0]
        return field_type

    def _get_root_configs(self) -> list[type[ConfigClass]]:
        nested_configs = set[type[ConfigClass]]()
        for config_class in self._configs:
            for field in fields(config_class):
                field_type = ConfigParser._unwrap_optional(field.type)
                if is_configclass_type(field_type):
                    nested_configs.add(field_type)

        return [c for c in self._configs if c not in nested_configs]

    def _convert_field_value(self, value: Any, field_type: type) -> Any:
        if is_dataclass(field_type):
            return self._parse_config(cast(type[ConfigClass], field_type), value)
        elif field_type is bool and not isinstance(value, bool):
            return self._parse_bool(value)
        elif isinstance(field_type, type) and not isinstance(value, field_type):
            return field_type(value)
        return value

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    def _parse_config(
        self, config_class: type[ConfigClass[T]], section_data: dict[str, Any]
    ) -> T:
        field_mappings = config_class.__config__.field_mappings
        field_deserializers = config_class.__config__.field_deserialzers
        kwargs = {}

        for field in fields(config_class):
            key = field_mappings.get(field.name, field.name)

            if key not in section_data:
                continue

            value = section_data[key]

            if field.name in field_deserializers:
                value = field_deserializers[field.name](value, parser=self)
            else:
                field_type = ConfigParser._unwrap_optional(field.type)
                value = self._convert_field_value(value, field_type)

            kwargs[field.name] = value

        return cast(T, config_class(**kwargs))

    def get(self, config_class: type[T]) -> T:
        """
        Generic method to get any registered config.

        Example:
            parser = ConfigParser()
            logger_config = parser.get(LoggerConfig)
            img_config = parser.get(ImageProcessingConfig)
        """

        if config_class not in self._configs:
            raise ValueError(
                f"Config class {config_class.__name__} was not provided to this parser"
            )

        cast_class = cast(type[ConfigClass[T]], config_class)

        section_name = cast_class.__config__.name

        if section_name not in self._config:
            raise ValueError(f"Missing {section_name} configuration from config file")

        section_data = self._config[section_name]
        return self._parse_config(cast_class, section_data)
