from typing import TYPE_CHECKING
from .registry import _Registry

if TYPE_CHECKING:
    from .decorator import ConfigclassInstance

_registry: _Registry[str, type[ConfigclassInstance]] = _Registry()
