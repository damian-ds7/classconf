from pathlib import Path
from typing import Any

import tomli_w
import tomllib


class TOMLFormat:
    extension = ".toml"

    def read(self, path: Path) -> dict[str, dict[str, Any]] | None:
        if not path.exists():
            return None

        with open(path, "rb") as f:
            return tomllib.load(f)

    def write(self, path: Path, data: dict[str, dict[str, Any]]) -> None:
        with open(path, "wb") as f:
            return tomli_w.dump(data, f)
