import pytest

from customer_compare.config import ConfigError, load_config

MINIMAL = """
key:
  source: CustomerID
source:
  type: excel
  path: data/samples/customer_SOURCE_DATA.xlsx
target:
  type: excel
  path: data/samples/customer_TARGET_DATA.xlsx
columns:
{columns}
"""


def write_config(tmp_path, columns="  - {source: Name, transform: upper}", extra=""):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "test.yaml"
    path.write_text(MINIMAL.format(columns=columns) + extra, encoding="utf-8")
    return path


def test_rejects_unknown_transform(tmp_path):
    path = write_config(tmp_path, columns="  - {source: Name, transform: reverse}")
    with pytest.raises(ConfigError, match="transform"):
        load_config(path)


def test_transform_not_allowed_on_numeric(tmp_path):
    path = write_config(tmp_path, columns="  - {source: Balance, transform: upper, compare: numeric}")
    with pytest.raises(ConfigError, match="text columns"):
        load_config(path)


def test_missing_environment_variable_without_default(tmp_path):
    path = write_config(
        tmp_path,
        extra="",
    )
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "path: data/samples/customer_SOURCE_DATA.xlsx",
            "path: \"${COMPARE_TEST_UNSET_VAR}\"",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="COMPARE_TEST_UNSET_VAR"):
        load_config(path)


def test_environment_variable_default_is_used(tmp_path, monkeypatch):
    monkeypatch.delenv("COMPARE_TEST_UNSET_VAR", raising=False)
    path = write_config(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "path: data/samples/customer_SOURCE_DATA.xlsx",
            "path: \"${COMPARE_TEST_UNSET_VAR:-data/samples/customer_SOURCE_DATA.xlsx}\"",
        ),
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.source.path.name == "customer_SOURCE_DATA.xlsx"
