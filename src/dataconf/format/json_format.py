from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config_format import ConfigFormat


class JSONFormat(ConfigFormat):
    """Read and write JSON configuration files."""

    def read(self, path: Path) -> dict[str, dict[str, Any]] | None:
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write(self, path: Path, data: dict[str, dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
