from typing import Any, cast

from classconf.types import ConfigClass


def as_config_class(cls: type[Any]) -> type[ConfigClass[Any]]:
    return cast(type[ConfigClass[Any]], cls)
