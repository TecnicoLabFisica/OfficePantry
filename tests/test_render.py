"""Renders the pages the way a browser would, with fetch, the DOM and the clock
stubbed.

test_ledger.py checks the arithmetic; this checks that the arithmetic actually
reaches the page -- the balance, the monthly summary, the breakdown and the
history are all produced by initBudget(), not by the pure functions alone.

Two things are held still so the suite stays honest as the project moves: the
ledger (see conftest.py) and the calendar. initIndex() and initBudget() ask
currentMonthKey() what month it is, so a test that does not pin the date is
really asserting something about the day it happens to run.
"""

import json

import pytest
from conftest import EMPTY_MONTH, LEDGER_MONTH, ROOT

quickjs = pytest.importorskip("quickjs", reason="quickjs is needed to run pantry.js")

HARNESS = """
var SLOTS = {};
var MARKUP_HREF = 'the href already in the markup';
function El(){
  this.textContent = '';
  this.innerHTML = '';
  this.href = MARKUP_HREF;
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
// A stopped clock. pantry.js only ever asks a Date for the year and the month,
// so this is the whole surface -- installed before pantry.js so that
// currentMonthKey() sees the month the test chose.
var NOW = {year: 2026, month: 3};
function Date(){}
Date.prototype.getFullYear = function(){ return NOW.year; };
Date.prototype.getMonth = function(){ return NOW.month; };
"""


def run_page(init, files, now=LEDGER_MONTH):
    """Run one page's init function. `now` is a "YYYY-MM" the clock reports."""
    year, month = (int(part) for part in now.split("-"))
    ctx = quickjs.Context()
    ctx.eval(f"var FILES = {json.dumps(files)};")
    ctx.eval(HARNESS)
    ctx.eval(f"NOW.year = {year}; NOW.month = {month - 1};")
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
def budget(fixture_files):
    return run_page("initBudget", fixture_files)


def test_balance_reaches_the_page(budget):
    assert slot(budget, "data-balance") == "$12.15"


def test_month_summary_totals(budget):
    html = slot(budget, "data-month-summary", "innerHTML")
    assert "+$15.00" in html          # contributions in, 2026-04
    assert "-$4.35" in html           # spent, 2026-04
    assert "$10.65" in html           # net


def test_month_summary_is_zero_in_a_month_with_no_rows(fixture_files):
    """The page must survive the calendar moving past the last entry.

    The balance carries across every month, so it does not change; only the
    "this month" panel empties out.
    """
    ctx = run_page("initBudget", fixture_files, now=EMPTY_MONTH)
    html = slot(ctx, "data-month-summary", "innerHTML")
    assert "+$0.00" in html
    assert "-$0.00" in html
    assert slot(ctx, "data-balance") == "$12.15"


def test_breakdown_labels_and_amounts(budget):
    html = slot(budget, "data-breakdown", "innerHTML")
    assert "☕ Coffee" in html         # the largest category, so it sorts first
    assert "$8.50" in html
    assert "$0.10" in html


def test_history_lists_every_transaction(budget):
    html = slot(budget, "data-history", "innerHTML")
    assert "Mixed nuts" in html
    assert "Cleo paid in" in html
    assert html.count('class="row"') == 9       # 5 contributions + 4 expenses


def test_history_is_newest_first(budget):
    html = slot(budget, "data-history", "innerHTML")
    assert html.index("Bag clips") < html.index("Coffee beans")


def test_quoted_comma_survives_to_the_page(budget):
    """An unquoted comma here would silently drop the row instead."""
    html = slot(budget, "data-history", "innerHTML")
    assert "Water, snacks" in html
    assert "$3.25" in html


def test_index_page_renders_balance(fixture_files):
    ctx = run_page("initIndex", fixture_files)
    assert slot(ctx, "data-balance") == "$12.15"


def test_missing_ledger_degrades_without_crashing(config_json):
    ctx = run_page("initBudget", {"data/config.json": config_json})
    assert slot(ctx, "data-balance") == "—"
    assert "Could not load" in slot(ctx, "data-history", "innerHTML")


def test_suggestions_page_without_a_form_url_explains_itself(config_json):
    """Blanks the URL rather than trusting data/config.json to be empty --
    linking the real form is a data change, not a reason for a test to fail."""
    cfg = json.loads(config_json)
    cfg["suggestionFormUrl"] = ""
    ctx = run_page("initSuggestions", {"data/config.json": json.dumps(cfg)})
    assert "not been linked yet" in slot(ctx, "data-form", "innerHTML")


def test_suggestions_page_embeds_a_configured_form(config_json):
    cfg = json.loads(config_json)
    cfg["suggestionFormUrl"] = "https://docs.google.com/forms/d/e/ABC/viewform?embedded=true"
    ctx = run_page("initSuggestions", {"data/config.json": json.dumps(cfg)})
    html = slot(ctx, "data-form", "innerHTML")
    assert "<iframe" in html
    assert "docs.google.com/forms/d/e/ABC" in html


def test_edit_history_link_follows_the_configured_repository(budget, config_json):
    """The transparency link must not stay pinned to whatever repo it was
    written for -- if the project moves, a 404 breaks the audit trail."""
    expected = json.loads(config_json)["repoUrl"] + "/commits/main/data"
    assert slot(budget, "data-repo-link", "href") == expected


def test_edit_history_link_falls_back_when_repo_url_is_unset(config_json):
    cfg = json.loads(config_json)
    cfg.pop("repoUrl")
    ctx = run_page("initBudget", {"data/config.json": json.dumps(cfg)})
    assert slot(ctx, "data-repo-link", "href") == "the href already in the markup"
