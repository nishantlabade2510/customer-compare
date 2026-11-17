"""Load and validate the YAML configuration.

Any string value may use ${VAR} or ${VAR:-default}, so connection details and
file locations can come from the CI environment instead of the repository.
Relative paths are resolved from the project root (the folder that holds config/).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .values import TRANSFORMS

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
COMPARE_TYPES = ("text", "numeric", "date")
SIDE_TYPES = ("sqlite", "database", "excel", "csv")


class ConfigError(ValueError):
    """The configuration is missing, malformed, or points at unusable inputs."""


@dataclass(frozen=True)
class SideConfig:
    name: str
    type: str
    url: str | None = None            # SQLAlchemy URL (type: database)
    path: Path | None = None          # SQLite file, Excel or CSV file
    query_file: Path | None = None    # SQL file (sqlite and database types)
    params: dict[str, Any] = field(default_factory=dict)
    sheet: str | int = 0              # Excel sheet name or index


@dataclass(frozen=True)
class ColumnRule:
    """How one source column maps to one target column.

    transforms are applied, in order, to the source value before comparison. This
    is how the expected transformation (for example TRIM then UPPER) is validated.
    """

    source: str
    target: str
    transforms: tuple[str, ...] = ()
    compare: str = "text"
    tolerance: float = 0.0

    @property
    def check_label(self) -> str:
        return f"TRANSFORM({','.join(self.transforms)})" if self.transforms else "COLUMN"


@dataclass(frozen=True)
class Config:
    name: str
    source_key: str
    target_key: str
    source: SideConfig
    target: SideConfig
    columns: tuple[ColumnRule, ...]
    not_null_source: tuple[str, ...]
    not_null_target: tuple[str, ...]
    check_duplicates: bool
    report_passes: bool
    fail_on_mismatch: bool
    output_dir: Path
    report_file: str
    config_path: Path


def load_config(config_path: str | Path) -> Config:
    path = Path(config_path).resolve()
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a mapping at the top level")

    raw = _expand_env(raw)
    root = path.parent.parent
    run = _section(raw, "run", required=False)
    key = _section(raw, "key")
    not_null = _section(raw, "not_null", required=False)

    source_key = key.get("source")
    if not source_key:
        raise ConfigError("key.source is required")

    return Config(
        name=str(run.get("name", "customer_compare")),
        source_key=str(source_key),
        target_key=str(key.get("target", source_key)),
        source=_load_side("source", raw.get("source"), root),
        target=_load_side("target", raw.get("target"), root),
        columns=_load_columns(raw.get("columns")),
        not_null_source=tuple(str(c) for c in not_null.get("source") or []),
        not_null_target=tuple(str(c) for c in not_null.get("target") or []),
        check_duplicates=bool(run.get("check_duplicates", True)),
        report_passes=bool(run.get("report_passes", True)),
        fail_on_mismatch=bool(run.get("fail_on_mismatch", True)),
        output_dir=root / str(run.get("output_dir", "reports")),
        report_file=str(run.get("report_file", "customer_mismatch_report.xlsx")),
        config_path=path,
    )


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def _substitute(match: re.Match[str]) -> str:
            name, default = match.group(1), match.group(2)
            env_value = os.environ.get(name)
            if env_value:
                return env_value
            if default is not None:
                return default
            raise ConfigError(f"Environment variable {name} is not set and has no default")

        return _ENV_PATTERN.sub(_substitute, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _section(raw: dict[str, Any], name: str, required: bool = True) -> dict[str, Any]:
    value = raw.get(name)
    if value is None:
        if required:
            raise ConfigError(f"Missing '{name}' section")
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"'{name}' must be a mapping")
    return value


def _load_side(name: str, data: Any, root: Path) -> SideConfig:
    if not isinstance(data, dict):
        raise ConfigError(f"'{name}' section must be a mapping")
    kind = data.get("type")
    if kind not in SIDE_TYPES:
        raise ConfigError(f"{name}.type must be one of {', '.join(SIDE_TYPES)}")

    params = dict(data.get("params") or {})
    if kind in ("sqlite", "database"):
        query = data.get("query_file")
        if not query:
            raise ConfigError(f"{name}.query_file is required for type '{kind}'")
        query_path = root / str(query)
        if not query_path.is_file():
            raise ConfigError(f"{name}.query_file not found: {query_path}")
        if kind == "database":
            if not data.get("url"):
                raise ConfigError(f"{name}.url is required for type 'database'")
            return SideConfig(name, kind, url=str(data["url"]), query_file=query_path, params=params)
        if not data.get("path"):
            raise ConfigError(f"{name}.path is required for type 'sqlite'")
        return SideConfig(name, kind, path=root / str(data["path"]), query_file=query_path, params=params)

    if not data.get("path"):
        raise ConfigError(f"{name}.path is required for type '{kind}'")
    return SideConfig(name, kind, path=root / str(data["path"]), sheet=data.get("sheet", 0))


def _load_columns(items: Any) -> tuple[ColumnRule, ...]:
    if not items:
        raise ConfigError("At least one entry under 'columns' is required")
    rules = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or "source" not in item:
            raise ConfigError(f"columns[{index}] must be a mapping with a 'source' key")
        transforms = item.get("transform") or []
        if isinstance(transforms, str):
            transforms = [transforms]
        for name in transforms:
            if name not in TRANSFORMS or name == "none":
                raise ConfigError(
                    f"columns[{index}].transform '{name}' is not one of "
                    f"{', '.join(n for n in TRANSFORMS if n != 'none')}"
                )
        rule = ColumnRule(
            source=str(item["source"]),
            target=str(item.get("target", item["source"])),
            transforms=tuple(str(t) for t in transforms),
            compare=str(item.get("compare", "text")),
            tolerance=float(item.get("tolerance", 0.0)),
        )
        if rule.compare not in COMPARE_TYPES:
            raise ConfigError(f"columns[{index}].compare '{rule.compare}' is not one of {', '.join(COMPARE_TYPES)}")
        if rule.compare != "text" and rule.transforms:
            raise ConfigError(f"columns[{index}]: transform applies only to text columns ({rule.source})")
        rules.append(rule)
    return tuple(rules)
