from dataclasses import Field, dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Mapping,
    Protocol,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)
from collections.abc import Callable

if TYPE_CHECKING:
    from src.configreg.parser import ConfigParser


class FieldDeserializer(Protocol):
    def __call__(self, value: Any, *, parser: ConfigParser = ...) -> Any: ...


type FieldSerializer = Callable[[Any], Any]


T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class ConfigclassInstance(Protocol[T_co]):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]
    __config__: ClassVar[ConfigSpec]


@dataclass
class ConfigSpec:
    top_level: bool
    name: str
    field_mappings: Mapping[str, str]
    field_deserialzers: Mapping[str, FieldDeserializer]
    field_serializers: Mapping[str, FieldSerializer]


def _apply_config(
    cls: type[T],
    *,
    top_level: bool,
    name: str,
    field_name_mappings: Mapping[str, str] | None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None,
    field_serializers: Mapping[str, FieldSerializer] | None,
) -> type[ConfigclassInstance[T]]:
    resolved_name = name or cls.__name__
    if not top_level and resolved_name == "":
        raise ValueError("name can't be empty in a non-top-level package")
    setattr(
        cls,
        "__config__",
        ConfigSpec(
            top_level=top_level,
            name=resolved_name,
            field_mappings=field_name_mappings or {},
            field_deserialzers=field_deserialzers or {},
            field_serializers=field_serializers or {},
        ),
    )
    return cast(type[ConfigclassInstance[T]], cls)


@overload
def configclass(cls: type[T]) -> type[ConfigclassInstance[T]]: ...


@overload
def configclass(
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> Callable[[type[T]], type[ConfigclassInstance[T]]]: ...


def configclass(
    cls: type[T] | None = None,
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> type[ConfigclassInstance[T]] | Callable[[type[T]], type[ConfigclassInstance[T]]]:
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
        inner_cls: type[T],
    ) -> type[ConfigclassInstance[T]]:
        return _apply_config(
            inner_cls,
            top_level=top_level,
            name=name,
            field_name_mappings=field_name_mappings,
            field_deserialzers=field_deserialzers,
            field_serializers=field_serializers,
        )

    return decorator
