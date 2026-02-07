from pathlib import Path
from typing import Any, Protocol


class ConfigFormat(Protocol):
    def read(self, path: Path) -> dict[str, Any] | None: ...

    def write(self, path: Path, data: dict[str, Any]) -> None: ...
