from collections.abc import Callable, Mapping
from typing import (
    TypeVar,
    cast,
    overload,
)

from .types import ConfigClass, ConfigSpec, FieldDeserializer, FieldSerializer

_T = TypeVar("_T")


def _apply_config[_T](  # noqa: UP049
    cls: type[_T],
    *,
    top_level: bool,
    name: str,
    field_name_mappings: Mapping[str, str] | None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None,
    field_serializers: Mapping[str, FieldSerializer] | None,
) -> type[ConfigClass[_T]]:
    resolved_name = name or cls.__name__
    if not top_level and resolved_name == "":
        raise ValueError("name can't be empty in a non-top-level package")

    cast(type[ConfigClass[_T]], cls).__config__ = ConfigSpec(
        top_level=top_level,
        name=resolved_name,
        field_mappings=field_name_mappings or {},
        field_deserialzers=field_deserialzers or {},
        field_serializers=field_serializers or {},
    )

    return cast(type[ConfigClass[_T]], cls)


@overload
def configclass[_T](cls: type[_T]) -> type[ConfigClass[_T]]: ...  # noqa: UP049


@overload
def configclass(
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> Callable[[type[_T]], type[ConfigClass[_T]]]: ...


def configclass[_T](  # noqa: UP049
    cls: type[_T] | None = None,
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> type[ConfigClass[_T]] | Callable[[type[_T]], type[ConfigClass[_T]]]:
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
    ) -> type[ConfigClass[_T]]:
        return _apply_config(
            inner_cls,
            top_level=top_level,
            name=name,
            field_name_mappings=field_name_mappings,
            field_deserialzers=field_deserialzers,
            field_serializers=field_serializers,
        )

    return decorator
