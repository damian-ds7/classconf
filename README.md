# classconf

Dataclass companion for config metadata and parsing, with a `ConfigParser` that
generates and loads typed configs from files.

## Core ideas

- Use `@configclass` to attach config metadata to dataclasses.
- Provide config classes to `ConfigParser`.
- Parse config files into dataclass instances.

## Basic usage

```python
from dataclasses import dataclass
from pathlib import Path

from classconf import ConfigParser, configclass
from classconf.format import JSONFormat


@configclass
@dataclass
class PathsConfig:
    output_dir: Path = Path("./out")


@configclass(top_level=True)
@dataclass
class AppConfig:
    name: str = "demo"
    paths: PathsConfig = field(default_factory=PathsConfig)


parser = ConfigParser(
    "config.json",
    AppConfig,
    format=JSONFormat(),
    create_noexist=True,
)

config = parser.get(AppConfig)
```

Generated config

```json
{
  "name": "demo",
  "paths": {
    "output_dir": "out"
  }
}
```

## Formats

- `TOMLFormat` (default if `format` is `None`)
- `JSONFormat`

```python
from classconf.format import TOMLFormat

parser = ConfigParser("config.toml", AppConfig, PathsConfig, format=TOMLFormat())
```

`TOMLFormat` accepts `none_value` to control how `None` is written. Use
`none_value=None` to omit `None` fields entirely.

## Custom formats

To add a new format, implement `ConfigFormat` with `read` and `write` methods.
`read` should return `None` when the file does not exist.

```python
from pathlib import Path
from typing import Any

from classconf.format import ConfigFormat


class YAMLFormat(ConfigFormat):
    def read(self, path: Path) -> dict[str, Any] | None:
        ...

    def write(self, path: Path, data: dict[str, Any]) -> None:
        ...
```

## Field mappings, serializers, deserializers

```python
from dataclasses import dataclass
from classconf import ConfigParser, configclass
from classconf.format import JSONFormat


def deserialize_num(value: str, **_) -> int:
    return int(value.rstrip("x"))


def serialize_num(value: int) -> str:
    return f"{value}x"


@configclass(
    name="metrics",
    field_deserialzers={"count": deserialize_num},
    field_serializers={"count": serialize_num},
    field_name_mappings={"count": "count_value"},
)
@dataclass
class MetricsConfig:
    count: int = 3


parser = ConfigParser(
    "config.json",
    MetricsConfig,
    format=JSONFormat(),
    create_noexist=True,
)

metrics = parser.get(MetricsConfig)
```

Generated config file

```json
{
  "metrics": {
    "count_value": "3x"
  }
}
```

Deserializers can also accept a parser to resolve other configs. This is useful
when a field is typed as a protocol/ABC and a string selects which config
section to load.

```python
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from classconf import ConfigParser, configclass
from classconf.format import TOMLFormat


@runtime_checkable
class DatabaseConfig(Protocol):
    driver: ClassVar[str]


@configclass(name="sqlite")
@dataclass
class SQLiteConfig:
    driver: ClassVar[str] = "sqlite"
    path: str = "app.db"


@configclass(name="postgres")
@dataclass
class PostgresConfig:
    driver: ClassVar[str] = "postgres"
    host: str = "localhost"
    port: int = 5432


def resolve_database(name: str, parser: ConfigParser) -> DatabaseConfig:
    return parser.get(SQLiteConfig if name == "sqlite" else PostgresConfig)


def serialize_database(db: DatabaseConfig) -> str:
    return db.driver


@configclass(
    top_level=True,
    field_deserialzers={"database": resolve_database},
    field_serializers={"database": serialize_database},
)
@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=SQLiteConfig)


parser = ConfigParser(
    "config.json",
    AppConfig,
    SQLiteConfig,
    PostgresConfig,
    format=JSONFormat(),
    create_noexist=True,
)

config = parser.get(AppConfig)
print(config.database.driver)
```

Generated config

```toml
database = "sqlite"

[postgres]
driver = "postgres"
host = "localhost"
port = 5432

[sqlite]
driver = "sqlite"
path = "app.db"

```

## Generating configs from instances

`ConfigParser.generate_config` writes a config file from config class instances.
This is useful for preset generation when a CLI or UI offers a few known
configurations and only the selected one should be saved.

```python
from dataclasses import dataclass
from classconf import ConfigParser, configclass
from classconf.format import JSONFormat


@configclass(name="logging")
@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "app.log"


preset = "debug"  # could come from CLI/UI

if preset == "debug":
    config = LoggingConfig(level="DEBUG", file="debug.log")
else:
    config = LoggingConfig(level="INFO", file="app.log")

ConfigParser.generate_config(
    "logging_preset.json",
    config,
    format=JSONFormat(),
    override_existing=True,
)
```

## Adding configs later

```python
parser.add(OtherConfig)
other = parser.get(OtherConfig)
```

## Quirks and constraints

- Only one top-level config class is allowed per parser.
- `create_noexist=False` requires the file to exist.
- Missing config keys raise `KeyError` during parsing.
- `get()` raises if the class was not provided to the parser.
- With JSON/TOML, fields without defaults are written as `null`/`None`
  placeholders.
