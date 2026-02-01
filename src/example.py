from dataclasses import dataclass
from configreg.decorator import configclass


def field_parser(value: str, **_):
    return 5


@configclass(field_deserialzers={"field": field_parser})
@dataclass
class Example:
    field: str = "value"


print(Example().__config__)
