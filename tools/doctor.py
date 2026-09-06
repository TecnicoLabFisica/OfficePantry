#!/usr/bin/env python3
"""Check the ledger before it reaches the page.

The pages derive every number from data/contributions.csv and data/expenses.csv,
and those files are usually edited through the GitHub web UI where nothing checks
them. A malformed row does not raise an error in the browser -- it shifts the
columns, the amount parses to zero, and the balance is quietly wrong. This script
is what notices.

    python tools/doctor.py           # report everything
    python tools/doctor.py --quiet   # errors only, for CI

Exit status is 0 when there are no errors, 1 otherwise. Warnings never fail.
"""

import argparse
import csv
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CONTRIBUTIONS_HEADER = ["date", "name", "month", "amount"]
EXPENSES_HEADER = ["date", "description", "category", "amount"]

# Deliberately strict. "5,00", "$5.00" and "5.000" all reach toCents() as
# something, and something is worse than nothing when it is money.
AMOUNT_RE = re.compile(r"^\d+(\.\d{1,2})?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

REQUIRED_CONFIG_KEYS = ["fundName", "monthlyContribution", "currencySymbol",
                        "categories"]


class Report:
    """Collects findings so every problem is reported, not just the first."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, message):
        self.errors.append(f"{where}: {message}")

    def warn(self, where, message):
        self.warnings.append(f"{where}: {message}")

    def ok(self):
        return not self.errors


def read_rows(path, report):
    """Parse a ledger CSV the way assets/pantry.js does.

    Blank lines and lines starting with '#' are skipped there, so they are
    skipped here. Returns (header, [(line_number, fields)]) or None.
    """
    if not path.exists():
        report.error(rel(path), "file is missing")
        return None

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        parsed = [(reader.line_num, row) for row in reader]

    kept = [(n, r) for n, r in parsed
            if any(c.strip() for c in r) and not r[0].strip().startswith("#")]
    if not kept:
        report.error(rel(path), "file is empty")
        return None

    header = [c.strip() for c in kept[0][1]]
    return header, kept[1:]


def rel(path):
    return str(pathlib.Path(path).resolve().relative_to(ROOT))


def check_shape(path, header, rows, expected, report):
    """Header and field count. This is the check that catches the comma bug."""
    if header != expected:
        report.error(f"{rel(path)}:1",
                     f"header is {header}, expected {expected}")
        return False

    shape_ok = True
    for line_no, row in rows:
        if len(row) != len(expected):
            report.error(
                f"{rel(path)}:{line_no}",
                f"expected {len(expected)} fields, found {len(row)} "
                "-- quote any description containing a comma, and write "
                "amounts as 5.00 rather than 5,00")
            shape_ok = False
    return shape_ok


def check_date(where, value, report):
    if not DATE_RE.match(value):
        report.error(where, f"date {value!r} is not YYYY-MM-DD")
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        report.error(where, f"date {value!r} is not a real date")
        return None


def check_amount(where, value, report):
    if not AMOUNT_RE.match(value):
        report.error(
            where,
            f"amount {value!r} is not a plain number with at most two decimals "
            "-- the page reads this as $0.00 and the balance goes wrong")
        return 0
    return round(float(value) * 100)


def check_contributions(report):
    path = DATA / "contributions.csv"
    result = read_rows(path, report)
    if result is None:
        return 0
    header, rows = result
    if not check_shape(path, header, rows, CONTRIBUTIONS_HEADER, report):
        return 0

    total = 0
    seen = {}
    for line_no, row in rows:
        where = f"{rel(path)}:{line_no}"
        date_str, name, month, amount = (c.strip() for c in row)

        parsed_date = check_date(where, date_str, report)
        total += check_amount(where, amount, report)

        if not name:
            report.error(where, "name is empty")
        elif " " in name:
            report.error(
                where,
                f"name {name!r} looks like a full name -- first names only, "
                "this repository is public")

        if not MONTH_RE.match(month):
            report.error(where, f"month {month!r} is not YYYY-MM")
        elif parsed_date and month != date_str[:7]:
            report.error(where,
                         f"month {month!r} does not match date {date_str!r}")

        key = (name.lower(), month)
        if key in seen:
            report.warn(where,
                        f"{name} already has a {month} contribution on line "
                        f"{seen[key]} -- add a correcting row if this is a "
                        "duplicate, never delete one")
        else:
            seen[key] = line_no

    return total


def check_expenses(report, categories):
    path = DATA / "expenses.csv"
    result = read_rows(path, report)
    if result is None:
        return 0
    header, rows = result
    if not check_shape(path, header, rows, EXPENSES_HEADER, report):
        return 0

    total = 0
    for line_no, row in rows:
        where = f"{rel(path)}:{line_no}"
        date_str, description, category, amount = (c.strip() for c in row)

        check_date(where, date_str, report)
        total += check_amount(where, amount, report)

        if not description:
            report.error(where, "description is empty")

        if category not in categories:
            report.error(
                where,
                f"category {category!r} is not in data/config.json "
                f"({', '.join(sorted(categories))}) -- a typo becomes its own "
                "row in the breakdown instead of failing")

    return total


def check_config(report):
    """Returns the category keys, or an empty set if the config is unusable."""
    path = DATA / "config.json"
    if not path.exists():
        report.error(rel(path), "file is missing")
        return set()

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.error(f"{rel(path)}:{exc.lineno}",
                     f"is not valid JSON ({exc.msg}) -- all three pages break")
        return set()

    for key in REQUIRED_CONFIG_KEYS:
        if key not in cfg:
            report.error(rel(path), f"missing required key {key!r}")

    for key in ["suggestionFormUrl", "suggestionSheetCsvUrl"]:
        if not cfg.get(key):
            report.warn(rel(path),
                        f"{key} is empty -- the suggestions page explains "
                        "itself instead of working")

    if not cfg.get("repoUrl"):
        report.warn(rel(path),
                    "repoUrl is empty -- the edit history link on budget.html "
                    "falls back to the URL hardcoded in the page")

    return set(cfg.get("categories", {}))


def check_against_pantry_js(report, expected_cents):
    """Re-derive the balance with assets/pantry.js and compare.

    The Python arithmetic above is a second implementation of the money maths.
    Two implementations are only useful if they agree, so ask the one that
    actually ships. Skipped when quickjs is unavailable, so this script still
    runs on a bare python3.
    """
    try:
        import quickjs
    except ImportError:
        return None

    ctx = quickjs.Context()
    ctx.eval("var document={querySelector:function(){return null;}};"
             "var console={error:function(){},log:function(){}};")
    ctx.eval((ROOT / "assets/pantry.js").read_text(encoding="utf-8"))

    contributions = (DATA / "contributions.csv").read_text(encoding="utf-8")
    expenses = (DATA / "expenses.csv").read_text(encoding="utf-8")
    ctx.eval(
        f"var C=Pantry.parseCSV({json.dumps(contributions)});"
        f"var E=Pantry.parseCSV({json.dumps(expenses)});"
        "var L={contributions:C.map(function(r){"
        "  return {cents:Pantry.toCents(r.amount)};}),"
        "       expenses:E.map(function(r){"
        "  return {cents:Pantry.toCents(r.amount)};})};")
    actual = ctx.eval("Pantry.balance(L)")

    if actual != expected_cents:
        report.error(
            "assets/pantry.js",
            f"the page computes a balance of {actual} cents but the ledger "
            f"adds up to {expected_cents} -- the two disagree, so a row is "
            "being read differently than it was written")
    return actual


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true",
                        help="print errors only")
    args = parser.parse_args()

    report = Report()
    categories = check_config(report)
    contributed = check_contributions(report)
    spent = check_expenses(report, categories)

    balance = contributed - spent
    checked_by_js = None
    if report.ok():
        checked_by_js = check_against_pantry_js(report, balance)

    for line in report.errors:
        print(f"error  {line}", file=sys.stderr)
    if not args.quiet:
        for line in report.warnings:
            print(f"warn   {line}")

    if not report.ok():
        print(f"\n{len(report.errors)} error(s), "
              f"{len(report.warnings)} warning(s). The ledger is not safe to "
              "publish.", file=sys.stderr)
        return 1

    if not args.quiet:
        dollars = f"${balance // 100}.{balance % 100:02d}"
        via = "confirmed against assets/pantry.js" if checked_by_js is not None \
            else "quickjs not installed, page arithmetic not cross-checked"
        print(f"\nLedger is clean. Balance {dollars} ({via}).")
        if report.warnings:
            print(f"{len(report.warnings)} warning(s) above are open to-do "
                  "items, not failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
