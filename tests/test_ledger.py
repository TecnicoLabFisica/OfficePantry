"""Checks the browser's money math by running assets/pantry.js in a JS engine.

The page adds up other people's money, so the arithmetic is worth testing
directly rather than trusting a reimplementation of it in Python.

Everything below either uses the frozen ledger from conftest.py or asserts
something that stays true no matter what the real ledger says. Nothing here
asserts a particular balance for data/, because that number is supposed to
change every time somebody pays in.
"""

import csv
import json

import pytest
from conftest import CONTRIBUTIONS, EXPENSES, ROOT

quickjs = pytest.importorskip("quickjs", reason="quickjs is needed to run pantry.js")


@pytest.fixture(scope="module")
def js():
    ctx = quickjs.Context()
    # pantry.js only touches the DOM inside its init* functions; stub enough
    # for the module to evaluate.
    ctx.eval("var document={querySelector:function(){return null;}};"
             "var console={error:function(){},log:function(){}};")
    ctx.eval((ROOT / "assets/pantry.js").read_text())
    return ctx


def build_ledger(js, name, contributions, expenses):
    """Define a JS ledger object from two CSV strings and return its name."""
    js.eval(f"var {name} = (function(){{"
            f"  var C = Pantry.parseCSV({json.dumps(contributions)});"
            f"  var E = Pantry.parseCSV({json.dumps(expenses)});"
            "   return {"
            "     contributions: C.map(function(r){"
            "       return {cents: Pantry.toCents(r.amount)};}),"
            "     expenses: E.map(function(r){"
            "       return {cents: Pantry.toCents(r.amount), "
            "               category: r.category};})"
            "   };})();")
    return name


@pytest.fixture(scope="module")
def ledger(js):
    build_ledger(js, "ledger", CONTRIBUTIONS, EXPENSES)
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
    # contributions 5 x $5.00 = $25.00; expenses $8.50 + $3.25 + $1.00 + $0.10
    assert ledger.eval("Pantry.money(Pantry.balance(ledger))") == "$12.15"


def test_breakdown_is_sorted_by_size(ledger):
    assert ledger.eval("Pantry.byCategory(ledger.expenses)[0].category") == "coffee"
    assert ledger.eval(
        "Pantry.money(Pantry.byCategory(ledger.expenses)[0].cents)") == "$8.50"


def test_repeated_small_amounts_do_not_drift(js):
    """0.1 + 0.2 + 0.1 + 0.1 in float dollars is not 0.5. In cents it is."""
    js.eval("var d = {contributions:[{cents:0}], expenses:["
            "{cents:Pantry.toCents('0.10')},{cents:Pantry.toCents('0.20')},"
            "{cents:Pantry.toCents('0.10')},{cents:Pantry.toCents('0.10')}]};")
    assert js.eval("Pantry.money(-Pantry.balance(d))") == "$0.50"


def test_ledger_csvs_have_expected_columns():
    with open(ROOT / "data/contributions.csv") as fh:
        assert csv.DictReader(fh).fieldnames == ["date", "name", "month", "amount"]
    with open(ROOT / "data/expenses.csv") as fh:
        assert csv.DictReader(fh).fieldnames == ["date", "description", "category", "amount"]


def sum_cents(path):
    """Add up a shipped CSV the careful way, in integer cents."""
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    return sum(round(float(row["amount"]) * 100) for row in rows), len(rows)


def test_shipped_ledger_reads_the_same_way_it_was_written(js):
    """The real files, checked for consistency rather than for a total.

    Asserting a particular balance here would mean the first real contribution
    breaks the suite. What has to stay true as rows are added is that pantry.js
    reads the same total a careful reader would -- which is exactly what fails
    when a stray comma shifts the columns. tools/doctor.py says *why*; this says
    *that*.
    """
    contributed, n_in = sum_cents(ROOT / "data/contributions.csv")
    spent, n_out = sum_cents(ROOT / "data/expenses.csv")

    build_ledger(js, "shipped",
                 (ROOT / "data/contributions.csv").read_text(),
                 (ROOT / "data/expenses.csv").read_text())

    assert js.eval("shipped.contributions.length") == n_in
    assert js.eval("shipped.expenses.length") == n_out
    assert js.eval("Pantry.balance(shipped)") == contributed - spent


def test_no_shipped_row_is_read_as_zero(js):
    """A row worth $0.00 is what a malformed amount looks like from the page."""
    build_ledger(js, "shipped_nonzero",
                 (ROOT / "data/contributions.csv").read_text(),
                 (ROOT / "data/expenses.csv").read_text())
    for side in ["contributions", "expenses"]:
        zeros = js.eval(
            f"shipped_nonzero.{side}.filter(function(r){{return r.cents === 0;}}).length")
        assert zeros == 0, f"a row in data/{side}.csv is read as $0.00"
