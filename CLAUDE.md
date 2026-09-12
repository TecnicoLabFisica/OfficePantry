# Office Pantry

A shared office snack fund: a static GitHub Pages site over two CSV files.
No server, no database, no build step, no framework, no dependencies at runtime.
`assets/pantry.js` fetches the CSVs and derives every number on each page load.

## Commands

```bash
conda activate office-pantry     # or: micromamba activate office-pantry
pytest -q                        # runs assets/pantry.js in quickjs
ruff check .
python tools/doctor.py           # validates the ledger, says who still owes
python tools/doctor.py --month 2026-08   # ask about a month that has passed
python -m http.server 8000       # then open http://localhost:8000
```

`file://` does not work. The pages fetch the CSVs, which needs a real HTTP server.

## How a page works

`assets/pantry.js` is one IIFE assigning `const Pantry`, exposing a single `init*` per
page. Each HTML file ends with `<script>Pantry.initBudget()</script>` and marks its
slots with data attributes (`[data-balance]`, `[data-history]`, `[data-repo-link]`)
that the init function fills. Adding a page means adding an `init*` and its attributes,
not a router.

## Invariants

These are load-bearing. Breaking one is a bug even when nothing fails.

- **The balance is never stored.** It is `sum(contributions) − sum(expenses)`,
  recomputed on every load. Never add a cached or written-down total.
- **Money is integer cents** from `toCents()` to `money()`. Never sum float dollars.
- **Corrections are new rows.** Never edit or delete a past ledger row — the commit
  history of `data/` is the audit trail, and `budget.html` links to it as a promise.
- **First names only** in `data/contributions.csv`. The repository is public.
- **Dates are `YYYY-MM-DD`; amounts are plain numbers** (`5.00`, not `$5.00` or `5,00`).
- **Quote any description containing a comma**: `"Water, snacks"`. An unquoted comma
  shifts the columns, `amount` parses to `0`, and the expense silently disappears from
  the page with no error. This is the failure mode `tools/doctor.py` exists to catch.

## Rules

- After changing anything under `data/`, run `python tools/doctor.py`. A `PostToolUse`
  hook does this automatically, but check the output.
- Do not add dependencies, a build step, a framework, or a backend. Costing nothing to
  host and needing no maintenance is the constraint the whole design was rebuilt
  around — see the revision note at the top of `Plan-Office-Pantry.md`.
- Tests must not assert against the live ledger or the real calendar. Use the frozen
  fixture in `tests/conftest.py` and pass `now=` to `run_page`. Asserting `"$9.15"` or
  a row count against `data/` means the first real contribution breaks the suite.
- `data/config.json` holds anything deployment-specific (form URLs, `repoUrl`,
  categories, currency) and `members`, the roster of who chips in each month.
  Do not hardcode those in the HTML or the JS.
- **Somebody has paid when their rows for the month add up to
  `monthlyContribution`**, not when a row exists. Payments arrive in parts, so two
  rows for one person in one month are correct and `doctor.py` reports the
  remainder. The roster never reaches a page — the repository is public.

## Layout

```
index.html budget.html suggestions.html   the three pages
assets/pantry.js                          CSV parsing, money maths, rendering
assets/style.css                          mobile-first styling
data/*.csv                                the ledger; data/config.json the settings
tools/doctor.py                           ledger validator
tools/make_qr.py                          QR sticker generator
tests/conftest.py                         the frozen fixture ledger
.github/workflows/ci.yml                  ruff + pytest + doctor on every push
Plan-Office-Pantry.md                     design document and its rationale
Status-Office-Pantry.md                   open setup tasks that are the admin's to do
```

## Skills

`pantry-doctor` for diagnosing a live problem, `record-ledger-entry` for adding money
correctly. The `ledger-auditor` agent reviews a `data/` diff before it is committed.
