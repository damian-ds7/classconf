from collections.abc import Callable, Mapping
from dataclasses import Field, dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from .parser import ConfigParser


class FieldDeserializer(Protocol):
    def __call__(self, value: Any, /, *, parser: ConfigParser = ...) -> Any: ...


type FieldSerializer = Callable[[Any], Any]

_T_co = TypeVar("_T_co", covariant=True)


@runtime_checkable
class ConfigClass(Protocol[_T_co]):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]
    __config__: ClassVar[ConfigSpec]


@dataclass
class ConfigSpec:
    top_level: bool
    name: str
    field_mappings: Mapping[str, str]
    field_deserialzers: Mapping[str, FieldDeserializer]
    field_serializers: Mapping[str, FieldSerializer]
