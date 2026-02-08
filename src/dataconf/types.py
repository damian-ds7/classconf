from collections.abc import Callable, Mapping
from dataclasses import Field
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NamedTuple,
    Protocol,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from .parser import ConfigParser


type FieldDeserializer = Deser1 | Deser2
type Deser1 = Callable[[Any], Any]
type Deser2 = Callable[[Any, ConfigParser], Any]

type FieldSerializer = Callable[[Any], Any]

_T_co = TypeVar("_T_co", covariant=True)


@runtime_checkable
class ConfigClass(Protocol[_T_co]):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]
    __config__: ClassVar[ConfigSpec]


ConfigSpec = NamedTuple(
    "ConfigSpec",
    [
        ("top_level", bool),
        ("name", str),
        ("field_mappings", Mapping[str, str]),
        ("field_deserialzers", Mapping[str, FieldDeserializer]),
        ("field_serializers", Mapping[str, FieldSerializer]),
    ],
)
