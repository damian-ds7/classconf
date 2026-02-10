from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from classconf import ConfigParser, configclass
from classconf.format import JSONFormat


@configclass
@dataclass
class Nested:
    value: int = 1


@configclass(top_level=True)
@dataclass
class AppConfig:
    name: str = "demo"
    nested: Nested = field(default_factory=Nested)


def main() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.json"
        parser = ConfigParser(
            path,
            AppConfig,
            Nested,
            format=JSONFormat(),
            create_noexist=True,
        )
        config = parser.get(AppConfig)
        assert config.name == "demo"
        assert config.nested.value == 1


if __name__ == "__main__":
    main()
