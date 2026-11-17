# Customer Source vs Target Comparison

Automated reconciliation of `customer_source` against `customer_target`. It loads both sides,
runs the checks below, writes a mismatch report in the agreed layout, and fails the CI job
when a check fails.

Contact: neha_garg1@homedepot.com

## Requirements covered

| Requirement | Where it is done | Config |
|---|---|---|
| Connect to two databases | `connectors.py`: SQLite, any SQLAlchemy database, Excel, CSV | `source:` / `target:` |
| Compare record counts | `engine.py`: row count and distinct key count | n/a |
| Identify missing records | `engine.py`: keys in source and absent from target (and extras) | `key:` |
| Identify duplicates | `engine.py`: duplicate keys on each side, with full rows in the *Duplicates* sheet | `run.check_duplicates` |
| Compare selected columns | `engine.py`: one row per customer per column | `columns:` |
| Validate NULL constraints | `engine.py`: NOT NULL on each side, *NULL Violations* sheet | `not_null:` |
| Validate transformations | `values.py`: transforms applied to the source value must equal the target | `columns[].transform` |
| Generate a mismatch report | `report.py`: Excel (6 sheets), CSV, JSON summary | `run.report_file` |
| Externalise SQL and config | `sql/*.sql`, `config/*.yaml`, `${ENV_VAR}` substitution | all of the above |
| Run through CI/CD | `.github/workflows/customer-compare.yml`, exit codes 0/1/2 | `run.fail_on_mismatch` |

## Mismatch report format

The main sheet follows the requested layout, with one extra column (`Check`) that says which rule
produced the row.

| Customer ID | Column | Source | Target | Status | Check |
|---|---|---|---|---|---|
| 1001 | CustomerName | Neha Garg | NEHA GARG | Pass | TRANSFORM(trim,upper) |
| 1002 | Balance | 637.53 | 687.53 | Fail | COLUMN |
| 1024 | Country | canada | NULL | Fail | TRANSFORM(trim,upper) |
| 1030 | (record) | PRESENT | MISSING | Fail | MISSING |
| 1005 | CustomerID | 1 row(s) | 2 row(s) | Fail | DUPLICATE |

Workbook sheets: **Summary** (every check with Pass/Fail/Warn), **Mismatch Report** (all compared
cells plus missing and duplicate rows), **Failures Only**, **Missing Records** (full records),
**Duplicates** (full records), **NULL Violations**.

## Results on the supplied sample data

Run: `python -m customer_compare --config config/config.yaml`, exit code 1.

| Check | Result | Detail |
|---|---|---|
| Row count | Pass | 30 vs 30. **This hides the defects below.** |
| Distinct key count | Fail | 30 source keys vs 29 target keys |
| Missing records | Fail | 1030 is in source and not in target |
| Duplicate keys (target) | Fail | 1005 appears twice |
| Leading or trailing spaces | Warn | 210 source and 1 target values are padded |
| Column values and transformations | Fail | 9 of 290 compared cells |
| NULL constraints | Fail | 1009 Balance and 1024 Country are NULL in target |

Failing cells: 1002 Balance (637.53 vs 687.53), 1007 City (toronto vs MONTREAL), 1009 Balance
(1600.24 vs NULL), 1012 CustomerName (Asha Kumar vs Asha Rao), 1015 Email (amit.khan@ vs
Amit.Rao@), 1016 Balance (2562.95 vs 2442.45), 1018 DOB (2004-06-25 vs 1990-01-01), 1023 Balance
(3525.66 vs 3525.76), 1024 Country (canada vs NULL).

The source extract pads every text column with spaces (all 30 rows). This looks like a
fixed-width `CHAR` export. The config trims text before comparing, and the warning keeps the
padding visible so it can be fixed upstream.

## Quick start

```bash
pip install -r requirements.txt

# Build the local SQLite databases from the sample workbooks
python scripts/load_samples_to_db.py

# Database mode (default)
python -m customer_compare --config config/config.yaml

# Excel mode (no database needed)
python -m customer_compare --config config/config.excel.yaml

# Tests
pytest
```

Run commands from the project root. Reports are written to `reports/`.

## Project layout

```
config/
  config.yaml          database mode: connections, key, column rules, NOT NULL lists
  config.excel.yaml    same rules, reading the workbooks directly
sql/
  source_customers.sql  source extract (edit here, not in Python)
  target_customers.sql  target extract
customer_compare/
  config.py            YAML loading, ${ENV:-default} substitution, validation
  connectors.py        sqlite / database (SQLAlchemy) / excel / csv loaders
  values.py            NULL handling, key normalisation, transforms, comparison
  engine.py            the checks and report rows
  report.py            Excel, CSV and JSON output
  sample_loader.py     workbook -> SQLite helper
  __main__.py          command-line entry point
scripts/load_samples_to_db.py
data/samples/          the two supplied workbooks
tests/                 unit tests, sample-data regression tests, config tests
.github/workflows/customer-compare.yml
```

## Configuration

### Connections

Any value can use `${VAR}` (required) or `${VAR:-default}`. Secrets belong in CI variables, not in
the repository.

```yaml
source:
  type: database                       # sqlite | database | excel | csv
  url: ${SOURCE_DB_URL}
  query_file: sql/source_customers.sql
  params: {}                           # named bind parameters for the SQL, e.g. {load_date: 2026-11-01}
```

| Type | Needs | Example |
|---|---|---|
| `sqlite` | nothing extra | `path: data/source.db` |
| `database` | SQLAlchemy and a driver | `url: postgresql+psycopg2://user:pass@host:5432/db` |
| `excel` | openpyxl | `path: data/x.xlsx`, `sheet: SOURCE` |
| `csv` | nothing extra | `path: data/x.csv` |

Other SQLAlchemy URLs: `mssql+pyodbc://user:pass@DSN_NAME`,
`oracle+oracledb://user:pass@host:1521/?service_name=SVC`, `mysql+pymysql://user:pass@host/db`.

### Key

```yaml
key:
  source: CustomerID
  target: CustomerID   # may differ if the target uses another column name
```

Keys are normalised before matching: `1001`, `1001.0` and `" 1001 "` all match.

### Column rules

```yaml
columns:
  - {source: CustomerName, target: CustomerName, transform: [trim, upper], compare: text}
  - {source: Email,        target: Email,        transform: [trim, lower], compare: text}
  - {source: DOB,          target: DOB,          compare: date}
  - {source: Balance,      target: Balance,      compare: numeric, tolerance: 0.005}
```

- `transform` (text only) is applied to the **source** value, in order: `trim`, `upper`, `lower`.
  The target must equal the result exactly. A target that is not in the expected form, such as a
  mixed-case email, is a mismatch.
- `compare`: `text`, `numeric` (Decimal, optional `tolerance`), or `date` (time part ignored).
- NULL matches NULL only. A NULL on one side is always a mismatch.

### NOT NULL

```yaml
not_null:
  source: [CustomerID, CustomerName, Email]
  target: [CustomerID, CustomerCode, CustomerName, Email, Country, Balance]
```

### Run options

| Option | Default | Effect |
|---|---|---|
| `run.name` | `customer_compare` | Shown in the report and CI log |
| `run.output_dir` | `reports` | Output folder |
| `run.report_file` | `customer_mismatch_report.xlsx` | Excel file name (CSV and JSON use the same stem) |
| `run.report_passes` | `true` | Include Pass rows, as in the sample layout |
| `run.check_duplicates` | `true` | Run the duplicate checks |
| `run.fail_on_mismatch` | `true` | Exit 1 when any check fails |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | All checks passed (or `--report-only`, or `fail_on_mismatch: false`) |
| 1 | One or more checks failed. This fails the CI job. |
| 2 | Configuration or input error (bad YAML, missing env var, missing column or file) |

## CI/CD

`.github/workflows/customer-compare.yml` runs:

1. **unit-tests**: `pytest` on every push and pull request.
2. **reconcile**: loads the data, runs the comparison, uploads `reports/` as an artifact (even on
   failure), and fails the job on a mismatch. It also runs nightly.

To use real databases, add `SOURCE_DB_URL` and `TARGET_DB_URL` as repository secrets, switch both
sides to `type: database`, and replace the sample-load step with the real extract step. Add the
database driver to `requirements.txt`.

The CLI runs anywhere Python does (Jenkins, Azure DevOps, GitLab CI), so the workflow is a thin
wrapper around `python -m customer_compare`.

## Assumptions and limitations

- Column comparison uses the **first** row for each target key. Other copies of a duplicated key
  are reported by the Duplicate check, not compared column by column.
- Null-constraint rows are only added to the main report when the same cell does not already
  fail, so each defect appears once there. The *NULL Violations* sheet lists every violation.
- Padded values are shown as they are in the source and target, so the padding is visible to
  reviewers.
- `Row count` compares total rows. Equal counts can hide missing and duplicate rows, which is why
  the distinct key count and the key checks are separate.
- Large tables: the framework loads both sides into memory. For very large volumes, push the
  comparison into SQL (for example with `FULL OUTER JOIN`) or partition the extract by key range.

## Extending

- **New column**: add a line under `columns:` and a matching `SELECT` column in both SQL files.
- **New transform**: add a function to `TRANSFORMS` in `values.py` and a test in `tests/test_values.py`.
- **New source type**: add a branch in `connectors.load_side()` and allow the type in
  `config.SIDE_TYPES`.
