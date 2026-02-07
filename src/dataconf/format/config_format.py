from abc import ABC
from pathlib import Path
from typing import Any


from abc import abstractmethod


class ConfigFormat(ABC):
    @abstractmethod
    def read(self, path: Path) -> dict[str, Any] | None: ...

    @abstractmethod
    def write(self, path: Path, data: dict[str, Any]) -> None: ...
