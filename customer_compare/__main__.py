"""Command-line entry point.

    python -m customer_compare --config config/config.yaml

Exit codes:
    0  all checks passed (or --report-only / fail_on_mismatch: false)
    1  one or more checks failed
    2  configuration or input error
"""

from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .engine import run_comparison
from .report import write_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="customer_compare",
        description="Compare a source customer dataset with its target.",
    )
    parser.add_argument("--config", default="config/config.yaml", help="YAML config file")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Write the reports but always exit 0",
    )
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
        result = run_comparison(cfg)
    except ConfigError as exc:
        print(f"[config error] {exc}", file=sys.stderr)
        return 2

    paths = write_reports(result, cfg)

    print(f"Customer comparison: {result.config_name}")
    print(f"Overall: {'PASS' if result.passed else 'FAIL'}")
    for check in result.checks:
        mark = "WARN" if check.warning else ("PASS" if check.passed else "FAIL")
        print(f"  [{mark}] {check.name}: {check.detail}")
    print(f"Compared cells: {result.compared_cells}, failed: {result.failed_cells}")
    print("Reports:")
    for label, path in paths.items():
        print(f"  {label:<5} {path}")

    if args.report_only or not cfg.fail_on_mismatch or result.passed:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
