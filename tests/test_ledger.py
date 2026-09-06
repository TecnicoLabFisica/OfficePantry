"""Checks the browser's money math by running assets/pantry.js in a JS engine.

The page adds up other people's money, so the arithmetic is worth testing
directly rather than trusting a reimplementation of it in Python.
"""

import json
import pathlib

import pytest

quickjs = pytest.importorskip("quickjs", reason="quickjs is needed to run pantry.js")

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def js():
    ctx = quickjs.Context()
    # pantry.js only touches the DOM inside its init* functions; stub enough
    # for the module to evaluate.
    ctx.eval("var document={querySelector:function(){return null;}};"
             "var console={error:function(){},log:function(){}};")
    ctx.eval((ROOT / "assets/pantry.js").read_text())
    return ctx


@pytest.fixture(scope="module")
def ledger(js):
    contributions = (ROOT / "data/contributions.csv").read_text()
    expenses = (ROOT / "data/expenses.csv").read_text()
    js.eval(f"var C = Pantry.parseCSV({json.dumps(contributions)});"
            f"var E = Pantry.parseCSV({json.dumps(expenses)});"
            "var ledger = {"
            "  contributions: C.map(function(r){return {cents:Pantry.toCents(r.amount)};}),"
            "  expenses: E.map(function(r){"
            "    return {cents:Pantry.toCents(r.amount), category:r.category};})"
            "};")
    return js


@pytest.mark.parametrize("cents,formatted", [
    (0, "$0.00"),
    (5, "$0.05"),
    (915, "$9.15"),
    (100000, "$1000.00"),
    (-50, "-$0.50"),
])
def test_money_formatting(js, cents, formatted):
    assert js.eval(f"Pantry.money({cents})") == formatted


@pytest.mark.parametrize("text,cents", [
    ("0.10", 10),
    ("14.75", 1475),
    ("5.00", 500),
    ("$7.50", 750),
    ("abc", 0),
])
def test_amounts_parse_to_integer_cents(js, text, cents):
    assert js.eval(f"Pantry.toCents({json.dumps(text)})") == cents


def test_csv_handles_quoted_commas(js):
    js.eval('var q = Pantry.parseCSV(\'date,description,amount\\n'
            '2026-09-03,"Water, snacks",14.75\\n\');')
    assert js.eval("q[0].description") == "Water, snacks"
    assert js.eval("q[0].amount") == "14.75"


def test_csv_skips_comments_and_blank_lines(js):
    js.eval("var r = Pantry.parseCSV('# note\\na,b\\n1,2\\n\\n3,4\\n');")
    assert js.eval("r.length") == 2


def test_balance_matches_hand_computed_total(ledger):
    # contributions 8 x $5.00 = $40.00; expenses $8.50 + $14.75 + $7.50 + $0.10
    assert ledger.eval("Pantry.money(Pantry.balance(ledger))") == "$9.15"


def test_breakdown_is_sorted_by_size(ledger):
    assert ledger.eval("Pantry.byCategory(ledger.expenses)[0].category") == "drinks"
    assert ledger.eval(
        "Pantry.money(Pantry.byCategory(ledger.expenses)[0].cents)") == "$14.75"


def test_repeated_small_amounts_do_not_drift(js):
    """0.1 + 0.2 + 0.1 + 0.1 in float dollars is not 0.5. In cents it is."""
    js.eval("var d = {contributions:[{cents:0}], expenses:["
            "{cents:Pantry.toCents('0.10')},{cents:Pantry.toCents('0.20')},"
            "{cents:Pantry.toCents('0.10')},{cents:Pantry.toCents('0.10')}]};")
    assert js.eval("Pantry.money(-Pantry.balance(d))") == "$0.50"


def test_ledger_csvs_have_expected_columns():
    import csv
    with open(ROOT / "data/contributions.csv") as fh:
        assert csv.DictReader(fh).fieldnames == ["date", "name", "month", "amount"]
    with open(ROOT / "data/expenses.csv") as fh:
        assert csv.DictReader(fh).fieldnames == ["date", "description", "category", "amount"]
