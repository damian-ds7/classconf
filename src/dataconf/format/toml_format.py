from pathlib import Path
from typing import Any

import rtoml


class TOMLFormat:
    def read(self, path: Path) -> dict[str, dict[str, Any]] | None:
        if not path.exists():
            return None

        return rtoml.load(path, none_value="null")

    def write(self, path: Path, data: dict[str, dict[str, Any]]) -> None:
        rtoml.dump(data, path, none_value="null")
