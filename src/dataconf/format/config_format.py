from pathlib import Path
from typing import Any, Protocol


class ConfigFormat(Protocol):
    extension: str

    def read(self, path: Path) -> dict[str, Any] | None: ...

    def write(self, path: Path, data: dict[str, Any]) -> None: ...
