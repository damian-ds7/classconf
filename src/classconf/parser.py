from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
import inspect
from pathlib import Path
import types
from typing import (
    Any,
    TypeGuard,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from .format.config_format import ConfigFormat
from .format.toml_format import TOMLFormat
from .types import ConfigClass, Deser1, Deser2, FieldDeserializer
from .utils import is_configclass_type
from .exceptions import MultipleTopLevelConfigError, InvalidConfigClassError

T = TypeVar("T")


def wants_parser(d: FieldDeserializer) -> TypeGuard[Deser2]:
    try:
        sig = inspect.signature(d)
    except (TypeError, ValueError):
        return True

    params = list(sig.parameters.values())

    positional = [
        p
        for p in params
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
    return has_varargs or len(positional) >= 2


def apply_deserializer(d: FieldDeserializer, value: Any, parser: "ConfigParser") -> Any:
    if wants_parser(d):
        return d(value, parser)
    return cast(Deser1, d)(value)


class ConfigParser:
    """Parse config files into registered dataclasses."""

    def __init__(
        self,
        config_path: Path | str,
        *configs: type[Any],
        create_noexist: bool = False,
        format: ConfigFormat | None = None,
    ) -> None:
        """
        Args:
            config_path: path to the config file.
            *configs: config classes to include in this parser.
            create_noexist: if True, write defaults when missing.
            format: file format handler (defaults to TOML).
        """

        if format is None:
            format = TOMLFormat()
        config_path = Path(config_path)

        if not create_noexist and not config_path.exists():
            raise FileNotFoundError("Provided config file does not exist")

        self._config_path = config_path
        self._format = format

        self._add_configs(*configs)
        self._config = self._read_config()

    def _add_configs(self, *configs: type[ConfigClass]) -> None:
        invalid_configs: list[type] = []
        toplevel_configs: list[type] = []

        for cls in configs:
            if not is_configclass_type(cls):
                invalid_configs.append(cls)
            elif cls.__config__.top_level:
                toplevel_configs.append(cls)

        if invalid_configs:
            invalid = ", ".join(cls.__name__ for cls in invalid_configs)
            raise InvalidConfigClassError(
                f"Config classes must use @configclass: {invalid}"
            )

        if len(toplevel_configs) > 1:
            toplevel = ", ".join(cls.__name__ for cls in toplevel_configs)
            raise MultipleTopLevelConfigError(
                f"Only one top-level config class is allowed; found: {toplevel}"
            )

        self._configs = sorted(
            configs,
            key=lambda cls: (
                0 if cls.__config__.top_level else 1,
                cls.__config__.name.casefold(),
            ),
        )

    def _read_config(self) -> dict[str, Any]:
        config_data = self._format.read(self._config_path)
        if config_data is None:
            return self._create_default_config()

        return config_data

    def _create_default_config(self) -> dict[str, Any]:
        config_data: dict[str, Any] = {}

        for config_class in self._get_root_configs():
            config_class_data = ConfigParser._get_class_fields(config_class)

            if config_class.__config__.top_level:
                config_data = config_data | config_class_data
            else:
                section_name = config_class.__config__.name
                config_data[section_name] = config_class_data

        self._format.write(self._config_path, config_data)

        return config_data

    @staticmethod
    def _get_class_fields(
        config_class: type[ConfigClass[Any]],
    ) -> dict[str, Any]:
        class_data: dict[str, Any] = {}

        field_mappings = config_class.__config__.field_mappings
        field_serializers = config_class.__config__.field_serializers
        resolved_types = get_type_hints(config_class, include_extras=True)

        for field in fields(config_class):
            key = field_mappings.get(field.name, field.name)
            field_type = ConfigParser._unwrap_optional(resolved_types[field.name])
            value = ConfigParser._get_field_default_value(field, field_type)

            value = ConfigParser._serialize_field_value(
                value, field.name, field_serializers
            )
            class_data[key] = value

        return class_data

    @staticmethod
    def _get_field_default_value(field: Any, field_type: Any) -> Any:
        if field.default is not MISSING:
            return field.default
        elif is_dataclass(field_type):
            return ConfigParser._get_class_fields(cast(type[ConfigClass], field_type))
        elif field.default_factory is not MISSING:
            return field.default_factory()
        return None

    @staticmethod
    def _serialize_field_value(
        value: Any, field_name: str, field_serializers: Mapping[str, Any]
    ) -> Any:
        if field_name in field_serializers:
            return field_serializers[field_name](value)
        elif isinstance(value, Path):
            return str(value)
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
            resolved_types = get_type_hints(config_class, include_extras=True)
            for field in fields(config_class):
                field_type = ConfigParser._unwrap_optional(resolved_types[field.name])
                if is_configclass_type(field_type):
                    nested_configs.add(field_type)

        return [c for c in self._configs if c not in nested_configs]

    def _convert_field_value(self, value: Any, field_type: type) -> Any:
        if value is None:
            return None
        if is_dataclass(field_type):
            return self._parse_config(cast(type[ConfigClass], field_type), value)
        elif isinstance(field_type, type) and not isinstance(value, field_type):
            return field_type(value)
        return value

    def _parse_config(
        self, config_class: type[ConfigClass[T]], section_data: dict[str, Any]
    ) -> T:
        field_mappings = config_class.__config__.field_mappings
        field_deserializers = config_class.__config__.field_deserialzers
        kwargs = {}

        resolved_types = get_type_hints(config_class, include_extras=True)
        for field in fields(config_class):
            key = field_mappings.get(field.name, field.name)

            if key not in section_data:
                raise KeyError(
                    f"Missing config key '{key}' for '{config_class.__name__}'"
                )

            value = section_data[key]

            if field.name in field_deserializers:
                value = apply_deserializer(field_deserializers[field.name], value, self)
            else:
                field_type = ConfigParser._unwrap_optional(resolved_types[field.name])
                value = self._convert_field_value(value, field_type)

            kwargs[field.name] = value

        return cast(T, config_class(**kwargs))

    def add(self, *configs: type[Any]) -> None:
        self._add_configs(*configs, *self._configs)

    def get(self, config_class: type[T]) -> T:
        """
        Generic method to get any registered config.
        """

        if config_class not in self._configs:
            raise ValueError(
                f"Config class {config_class.__name__} was not provided to this parser"
            )

        cast_class = cast(type[ConfigClass[T]], config_class)

        if cast_class.__config__.top_level:
            config_data = self._config
            return self._parse_config(cast_class, config_data)

        section_name = cast_class.__config__.name
        if section_name not in self._config:
            raise KeyError(f"Missing {section_name} configuration from config file")

        config_data = self._config[section_name]
        return self._parse_config(cast_class, config_data)
