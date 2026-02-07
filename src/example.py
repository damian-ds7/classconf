from dataclasses import dataclass
from typing import Any

from dataconf.decorator import configclass
from dataconf.format.toml_format import TOMLFormat
from dataconf.parser import ConfigParser


def field_parser(value: str, **_: Any) -> int:
    return 5


@configclass(field_deserialzers={"field": field_parser})
@dataclass
class Example_one:
    field: str = "value"


@configclass
@dataclass
class Example_two:
    field: str = "value"


parser = ConfigParser(
    "config", Example_one, Example_two, format=TOMLFormat(), create_noexist=True
)

e = parser.get(Example_two)
print(e.field)


def print_field(e: Example_one):
    print(e.field)
