"""Normalises the business key on both sides and works out how the two datasets line up.

Everything that compares keys (counts, missing, extra, duplicates, column checks)
reads from the KeyIndex built here, so the key rules live in one place.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import Config
from .values import normalize_key

KEY_COLUMN = "_key"  # normalised key, added to both frames


@dataclass
class KeyIndex:
    source_all: pd.DataFrame        # every source row, including rows with a NULL key
    target_all: pd.DataFrame
    source_valid: pd.DataFrame      # rows with a usable key
    target_valid: pd.DataFrame
    source_counts: pd.Series        # rows per key
    target_counts: pd.Series
    source_keys: set[str]
    target_keys: set[str]
    missing_keys: set[str]          # in source, not in target
    extra_keys: set[str]            # in target, not in source
    duplicate_source_keys: set[str]
    duplicate_target_keys: set[str]
    source_first: dict[str, dict]   # first source row for each key
    target_first: dict[str, dict]   # first target row for each key

    @property
    def shared_keys(self) -> set[str]:
        return self.source_keys & self.target_keys

    @property
    def duplicate_keys(self) -> set[str]:
        return self.duplicate_source_keys | self.duplicate_target_keys

    @property
    def all_keys_sorted(self) -> list[str]:
        return natural_sort(self.source_keys | self.target_keys)


def build_key_index(cfg: Config, source: pd.DataFrame, target: pd.DataFrame) -> KeyIndex:
    source_all = source.assign(**{KEY_COLUMN: source[cfg.source_key].map(normalize_key)})
    target_all = target.assign(**{KEY_COLUMN: target[cfg.target_key].map(normalize_key)})
    source_valid = source_all[source_all[KEY_COLUMN].notna()]
    target_valid = target_all[target_all[KEY_COLUMN].notna()]

    source_counts = source_valid[KEY_COLUMN].value_counts()
    target_counts = target_valid[KEY_COLUMN].value_counts()
    source_keys = set(source_counts.index)
    target_keys = set(target_counts.index)

    return KeyIndex(
        source_all=source_all,
        target_all=target_all,
        source_valid=source_valid,
        target_valid=target_valid,
        source_counts=source_counts,
        target_counts=target_counts,
        source_keys=source_keys,
        target_keys=target_keys,
        missing_keys=source_keys - target_keys,
        extra_keys=target_keys - source_keys,
        duplicate_source_keys=set(source_counts[source_counts > 1].index),
        duplicate_target_keys=set(target_counts[target_counts > 1].index),
        source_first=_first_rows(source_valid),
        target_first=_first_rows(target_valid),
    )


def natural_sort(keys: set[str]) -> list[str]:
    """Numeric keys sort numerically (1002 before 1010); other keys sort after them."""
    return sorted(keys, key=lambda k: (0, int(k), "") if k.isdigit() else (1, 0, k))


def _first_rows(valid: pd.DataFrame) -> dict[str, dict]:
    return valid.drop_duplicates(KEY_COLUMN, keep="first").set_index(KEY_COLUMN).to_dict("index")
