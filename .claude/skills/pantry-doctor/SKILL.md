---
name: pantry-doctor
description: Use when something about the Office Pantry site is wrong or suspected wrong — the balance looks off, a page is blank or 404s, suggestions do not load, the QR does not work, or the tests fail. Walks symptom to cause to fix.
---

# Diagnosing Office Pantry

Work from the symptom. Do not guess — every branch below ends in a command whose
output tells you whether that branch is the cause.

## Always start here

```bash
python tools/doctor.py     # the ledger
pytest -q                  # the money maths and the rendering
ruff check .
```

`doctor.py` reports `file:line: what is wrong`, exits 1 on errors and 0 on warnings.
Warnings about `suggestionFormUrl` / `suggestionSheetCsvUrl` being empty are open
setup tasks in `Status-Office-Pantry.md`, not faults.

## Symptom to cause

| Symptom | First suspect | Confirm with |
|---|---|---|
| Balance is wrong or an expense is missing | An unquoted comma or a bad amount shifted the columns; the row parses to `$0.00` | `python tools/doctor.py` — look for `expected 4 fields, found 5` |
| A category appears twice in the breakdown | A typo (`cofee`) became its own category | `doctor.py` flags categories not in `data/config.json` |
| Site returns 404 | Repository is private, or Pages is not enabled | `gh repo view --json visibility`; Settings → Pages |
| Pages load but every number is `—` | The CSVs 404'd | Browser console, or `curl -I <site>/data/expenses.csv` |
| Page is blank when opened locally | Opened over `file://` | Serve it: `python -m http.server 8000` |
| Suggestions list is empty or errors | Google response sheet is not published to web, or the CSV URL is wrong | Fetch `suggestionSheetCsvUrl` directly; the form itself still works by design |
| Suggestion form does not appear | `suggestionFormUrl` is empty in `data/config.json` | The page says so in place of the form |
| *Edit history* link 404s | Repo private, or `repoUrl` in `data/config.json` is wrong | `curl -I <repoUrl>/commits/main/data` |
| Tests fail after a month boundary | A test is reading the real clock | Every render test must pass `now=` to `run_page`; see `tests/test_render.py` |
| Tests fail after adding real ledger rows | A test is asserting against `data/` | Move it onto the frozen fixture in `tests/conftest.py` |
| QR scans to the wrong place | Regenerate; the QR holds only the URL | `python tools/make_qr.py --url <pages-url>` |

## When the balance is wrong but doctor is clean

The Python and JavaScript sums agree (`doctor.py` cross-checks them via quickjs) and
every row parses. Then the ledger is right and the *data* is wrong: a payment was
never recorded, or was recorded twice. Check `doctor.py` warnings for a duplicate
name+month, then read `git log -p data/`.

## Never

Do not fix a ledger problem by editing or deleting the offending row's history.
Correct a mistake by adding a new row — the commit history of `data/` is what makes
the numbers trustworthy. Fixing a malformed row in place is fine; rewriting a real
past transaction is not.
