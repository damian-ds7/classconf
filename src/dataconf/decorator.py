from collections.abc import Callable, Mapping
from dataclasses import Field, dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Protocol,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)

from .state import _registry as registry

if TYPE_CHECKING:
    from .parser import ConfigParser


class FieldDeserializer(Protocol):
    def __call__(self, value: Any, *, parser: ConfigParser = ...) -> Any: ...


type FieldSerializer = Callable[[Any], Any]


_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


@runtime_checkable
class ConfigclassInstance(Protocol[_T_co]):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]
    __config__: ClassVar[ConfigSpec]


@dataclass
class ConfigSpec:
    top_level: bool
    name: str
    field_mappings: Mapping[str, str]
    field_deserialzers: Mapping[str, FieldDeserializer]
    field_serializers: Mapping[str, FieldSerializer]


def _apply_config[_T](  # noqa: UP049
    cls: type[_T],
    *,
    top_level: bool,
    name: str,
    field_name_mappings: Mapping[str, str] | None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None,
    field_serializers: Mapping[str, FieldSerializer] | None,
) -> type[ConfigclassInstance[_T]]:
    resolved_name = name or cls.__name__
    if not top_level and resolved_name == "":
        raise ValueError("name can't be empty in a non-top-level package")

    cast(type[ConfigclassInstance[_T]], cls).__config__ = ConfigSpec(
        top_level=top_level,
        name=resolved_name,
        field_mappings=field_name_mappings or {},
        field_deserialzers=field_deserialzers or {},
        field_serializers=field_serializers or {},
    )

    registry.register(cls.__name__, cast(type[ConfigclassInstance[_T]], cls))

    return cast(type[ConfigclassInstance[_T]], cls)


@overload
def configclass[_T](cls: type[_T]) -> type[ConfigclassInstance[_T]]: ...  # noqa: UP049


@overload
def configclass(
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> Callable[[type[_T]], type[ConfigclassInstance[_T]]]: ...


def configclass[_T](  # noqa: UP049
    cls: type[_T] | None = None,
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> type[ConfigclassInstance[_T]] | Callable[[type[_T]], type[ConfigclassInstance[_T]]]:
    if cls is not None:
        return _apply_config(
            cls,
            top_level=top_level,
            name=name,
            field_name_mappings=field_name_mappings,
            field_deserialzers=field_deserialzers,
            field_serializers=field_serializers,
        )

    def decorator(
        inner_cls: type[_T],
    ) -> type[ConfigclassInstance[_T]]:
        return _apply_config(
            inner_cls,
            top_level=top_level,
            name=name,
            field_name_mappings=field_name_mappings,
            field_deserialzers=field_deserialzers,
            field_serializers=field_serializers,
        )

    return decorator


# def get_all_registered() -> list[type]:
#     return list(_REGISTRY.keys())
#
#
# def is_registered(config_class: type) -> bool:
#     return config_class in _REGISTRY
#
#
# def is_top_level(config_class: type) -> bool:
#     return _REGISTRY[config_class][0]
#
#
# def get_section_name(config_class: type) -> str:
#     if not is_registered(config_class):
#         raise ValueError(f"Config class {config_class.__name__} is not registered")
#     return _REGISTRY[config_class][1]
#
#
# def get_field_mappings(config_class: type) -> dict[str, str]:
#     if not is_registered(config_class):
#         raise ValueError(f"Config class {config_class.__name__} is not registered")
#     return _REGISTRY[config_class][2]
#
#
# def get_field_deserialzers(config_class: type) -> dict[str, FieldParser]:
#     if not is_registered(config_class):
#         raise ValueError(f"Config class {config_class.__name__} is not registered")
#     return _REGISTRY[config_class][3]
#
#
# def get_field_serializers(config_class: type) -> dict[str, FieldSerializer]:
#     if not is_registered(config_class):
#         raise ValueError(f"Config class {config_class.__name__} is not registered")
#     return _REGISTRY[config_class][4]
