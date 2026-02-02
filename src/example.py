from dataclasses import dataclass
from typing import Any

from dataconf.decorator import configclass
from dataconf.format.toml_format import TOMLFormat
from dataconf.parser import ConfigParser


def field_parser(value: str, **_: Any) -> int:
    return 5


@configclass(field_deserialzers={"field": field_parser})
@dataclass
class Example:
    field: str = "value"


print(Example().__config__)

parser = ConfigParser("config", format=TOMLFormat(), create_noexist=True)
