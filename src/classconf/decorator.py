from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import (
    Any,
    TypeVar,
    cast,
    dataclass_transform,
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
) -> type[_T]:
    resolved_name = name or cls.__name__

    cast(type[ConfigClass[_T]], cls).__config__ = ConfigSpec(
        top_level=top_level,
        name=resolved_name,
        field_mappings=field_name_mappings or {},
        field_deserialzers=field_deserialzers or {},
        field_serializers=field_serializers or {},
    )

    return cls


@overload
def configclass[_T](cls: type[_T]) -> type[_T]: ...  # noqa: UP049


@overload
def configclass(
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
) -> Callable[[type[_T]], type[_T]]: ...


@dataclass_transform()
def configclass[_T](  # noqa: UP049
    cls: type[_T] | None = None,
    *,
    top_level: bool = False,
    name: str = "",
    field_name_mappings: Mapping[str, str] | None = None,
    field_deserialzers: Mapping[str, FieldDeserializer] | None = None,
    field_serializers: Mapping[str, FieldSerializer] | None = None,
    **dataclass_kwargs: Any,
) -> type[_T] | Callable[[type[_T]], type[_T]]:
    if cls is not None:
        cls = _apply_config(
            cls,
            top_level=top_level,
            name=name,
            field_name_mappings=field_name_mappings,
            field_deserialzers=field_deserialzers,
            field_serializers=field_serializers,
        )
        return dataclass(**dataclass_kwargs)(cls)

    def decorator(
        inner_cls: type[_T],
    ) -> type[_T]:
        inner_cls = _apply_config(
            inner_cls,
            top_level=top_level,
            name=name,
            field_name_mappings=field_name_mappings,
            field_deserialzers=field_deserialzers,
            field_serializers=field_serializers,
        )
        return dataclass(**dataclass_kwargs)(inner_cls)

    return decorator
