from pathlib import Path
from typing import Any

import rtoml

from .config_format import ConfigFormat


class TOMLFormat(ConfigFormat):
    """Read and write TOML configuration files."""

    def __init__(self, none_value: str | None = "null") -> None:
        """
        Args:
            none_value: controls how `None` values are serialized.
                `none_value=None` means `None` values are ignored.
        """
        self.none_value = none_value

    def read(self, path: Path) -> dict[str, dict[str, Any]] | None:
        if not path.exists():
            return None

        return rtoml.load(path, none_value=self.none_value)

    def write(self, path: Path, data: dict[str, dict[str, Any]]) -> None:
        rtoml.dump(data, path, none_value=self.none_value)
