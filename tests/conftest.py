"""A fixed ledger for the tests to assert against.

The tests used to assert against data/contributions.csv and data/expenses.csv
directly -- a balance of "$9.15", a history of exactly 12 rows. That made the
suite a hostage of the seed data: the first real contribution would have broken
five tests. The numbers below are frozen so the shipped ledger can change
freely, and one test in test_ledger.py checks the real files for internal
consistency instead of for a particular total.

    contributions   $25.00   ($15.00 of it in 2026-04)
    expenses        $12.85   ( $4.35 of it in 2026-04)
    balance         $12.15
"""

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

CONTRIBUTIONS = """date,name,month,amount
2026-03-01,Alice,2026-03,5.00
2026-03-02,Bob,2026-03,5.00
2026-04-01,Alice,2026-04,5.00
2026-04-02,Bob,2026-04,5.00
2026-04-03,Cleo,2026-04,5.00
"""

# The quoted description is deliberate: an unquoted comma there shifts the
# columns and silently drops the expense, so the render path is worth covering.
EXPENSES = """date,description,category,amount
2026-03-10,Coffee beans,coffee,8.50
2026-04-05,"Water, snacks",drinks,3.25
2026-04-06,Mixed nuts,snacks,1.00
2026-04-07,Bag clips,other,0.10
"""

LEDGER_MONTH = "2026-04"      # a month the fixture has rows in
EMPTY_MONTH = "2026-12"       # a month it does not


@pytest.fixture(scope="session")
def config_json():
    """The real config -- the category labels are what the pages render."""
    return (ROOT / "data/config.json").read_text()


@pytest.fixture(scope="session")
def fixture_files(config_json):
    return {
        "data/config.json": config_json,
        "data/contributions.csv": CONTRIBUTIONS,
        "data/expenses.csv": EXPENSES,
    }
