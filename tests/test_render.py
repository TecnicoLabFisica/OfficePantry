"""Renders the pages the way a browser would, with fetch and the DOM stubbed.

test_ledger.py checks the arithmetic; this checks that the arithmetic actually
reaches the page — the balance, the monthly summary, the breakdown and the
history are all produced by initBudget(), not by the pure functions alone.
"""

import json
import pathlib

import pytest

quickjs = pytest.importorskip("quickjs", reason="quickjs is needed to run pantry.js")

ROOT = pathlib.Path(__file__).resolve().parent.parent

HARNESS = """
var SLOTS = {};
function El(){
  this.textContent = '';
  this.innerHTML = '';
  this.classList = {toggle:function(){}, add:function(){}, remove:function(){}};
}
var document = {querySelector: function(sel){
  var key = sel.replace(/[\\[\\]]/g, '');
  if (!SLOTS[key]) SLOTS[key] = new El();
  return SLOTS[key];
}};
var console = {error:function(){}, log:function(){}};
function fetch(url){
  var body = FILES[url];
  return Promise.resolve({
    ok: body !== undefined,
    status: body === undefined ? 404 : 200,
    text: function(){ return Promise.resolve(body); }
  });
}
"""


def run_page(init, files):
    ctx = quickjs.Context()
    ctx.eval(f"var FILES = {json.dumps(files)};")
    ctx.eval(HARNESS)
    ctx.eval((ROOT / "assets/pantry.js").read_text())
    ctx.eval(f"Pantry.{init}();")
    for _ in range(500):                      # drain the promise queue
        if not ctx.execute_pending_job():
            break
    return ctx


def slot(ctx, name, prop="textContent"):
    name = json.dumps(name)
    return ctx.eval(f"(SLOTS[{name}] ? SLOTS[{name}].{prop} : '<<missing>>')")


@pytest.fixture(scope="module")
def real_files():
    return {
        "data/config.json": (ROOT / "data/config.json").read_text(),
        "data/contributions.csv": (ROOT / "data/contributions.csv").read_text(),
        "data/expenses.csv": (ROOT / "data/expenses.csv").read_text(),
    }


@pytest.fixture(scope="module")
def budget(real_files):
    return run_page("initBudget", real_files)


def test_balance_reaches_the_page(budget):
    assert slot(budget, "data-balance") == "$9.15"


def test_month_summary_totals(budget):
    html = slot(budget, "data-month-summary", "innerHTML")
    assert "+$20.00" in html          # contributions in, September
    assert "-$7.60" in html           # spent, September
    assert "$12.40" in html           # net


def test_breakdown_labels_and_amounts(budget):
    html = slot(budget, "data-breakdown", "innerHTML")
    assert "💧 Drinks" in html
    assert "$14.75" in html
    assert "$0.10" in html


def test_history_lists_every_transaction(budget):
    html = slot(budget, "data-history", "innerHTML")
    assert "Mixed nuts" in html
    assert "Maria paid in" in html
    assert html.count('class="row"') == 12      # 8 contributions + 4 expenses


def test_history_is_newest_first(budget):
    html = slot(budget, "data-history", "innerHTML")
    assert html.index("Bag clips") < html.index("Coffee beans")


def test_index_page_renders_balance(real_files):
    ctx = run_page("initIndex", real_files)
    assert slot(ctx, "data-balance") == "$9.15"


def test_missing_ledger_degrades_without_crashing(real_files):
    ctx = run_page("initBudget", {"data/config.json": real_files["data/config.json"]})
    assert slot(ctx, "data-balance") == "—"
    assert "Could not load" in slot(ctx, "data-history", "innerHTML")


def test_suggestions_page_without_a_form_url_explains_itself(real_files):
    ctx = run_page("initSuggestions", real_files)
    assert "not been linked yet" in slot(ctx, "data-form", "innerHTML")


def test_suggestions_page_embeds_a_configured_form():
    cfg = json.loads((ROOT / "data/config.json").read_text())
    cfg["suggestionFormUrl"] = "https://docs.google.com/forms/d/e/ABC/viewform?embedded=true"
    ctx = run_page("initSuggestions", {"data/config.json": json.dumps(cfg)})
    html = slot(ctx, "data-form", "innerHTML")
    assert "<iframe" in html
    assert "docs.google.com/forms/d/e/ABC" in html
