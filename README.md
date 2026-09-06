# 🥨 Office Pantry

A shared office snack fund, run from a static web page and two CSV files.

Everyone chips in $5 a month. A QR sticker on the wall opens a page showing
exactly how much is left, where it went, and a form for suggesting what to buy
next.

**Live site:** https://tecnicolabfisica.github.io/OfficePantry/

---

## How it works

There is no server, no database and no login.

```
  QR sticker
      │
      ▼
  index.html ───────────► Google Form   (suggest something — no login)
  balance + buttons               │
      │                           ▼
      │                    Google Sheet ──published CSV──┐
      ├──► suggestions.html ◄──────────────────────────  ┘
      │
      └──► budget.html
                │
                ▼
      data/contributions.csv
      data/expenses.csv     (edited by the admin; git history is the audit trail)
```

Reading is public and static. The only thing coworkers write is a suggestion,
and that goes to a Google Form. Money is recorded by the admin as rows in CSV.

**The balance is never stored.** It is added up from the transactions on every
page load:

```
balance = sum(contributions) − sum(expenses)
```

Because the sum covers every month at once, a new month needs no action and
money cannot be double-counted at a month boundary.

---

## Admin: recording money

Both files live in `data/`. Edit them on github.com (pencil icon) or locally.

**Someone paid their $5** — add a line to `data/contributions.csv`:

```csv
date,name,month,amount
2026-09-14,Ana,2026-09,5.00
```

**You bought something** — add a line to `data/expenses.csv`:

```csv
date,description,category,amount
2026-09-14,Coffee beans,coffee,8.50
```

Rules that matter:

- **First names only.** This repository is public.
- Dates are `YYYY-MM-DD`; amounts are plain numbers, no `$`.
- Categories: `snacks`, `drinks`, `coffee`, `supplements`, `other`
  (edit the list in `data/config.json`).
- Wrap any description containing a comma in quotes: `"Water, snacks"`.
- Never delete or edit a past row to correct a mistake — add a correcting row.
  The commit history is what makes the ledger trustworthy.

Then check it:

```bash
python tools/doctor.py
```

A row like `2026-09-14,Water, snacks,drinks,9.00` — a comma that should have been
quoted — does not break the page. It shifts the columns, the amount reads as zero,
and the expense quietly disappears from the balance. `doctor.py` is what notices,
and it runs on every push, so a bad edit made on github.com fails the checks rather
than the ledger.

The page updates within a minute of the commit.

---

## Setup

### 1. Publish the site

The repository must be **public** — GitHub Pages only publishes from private
repositories on a paid plan.

Settings → Pages → Source: *Deploy from a branch* → `main` / `/ (root)`.

### 2. Connect the suggestion form

1. Create a Google Form with fields **Product** and **Category**.
2. Responses → *Get email notifications for new responses*, so you hear about
   suggestions without checking.
3. Copy the form's embed URL (Send → `<>`).
4. Open the linked response sheet → File → Share → **Publish to web** →
   the response sheet → **CSV** → copy the URL.
5. Put both into `data/config.json`:

```json
"suggestionFormUrl": "https://docs.google.com/forms/d/e/.../viewform?embedded=true",
"suggestionSheetCsvUrl": "https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv"
```

If the live list ever stops loading, the form keeps working — the page falls
back to a message rather than breaking.

### 3. Print the QR sticker

```bash
python tools/make_qr.py --url https://tecnicolabfisica.github.io/OfficePantry/
```

Writes `qr/office-pantry-qr.png`, an SVG, and `qr/print.html` — a print-ready
sheet with a caption. The QR contains only the URL, so the sticker survives any
change to the site.

---

## Development

```bash
conda env create -f environment.yaml
conda activate office-pantry

python -m http.server 8000     # then open http://localhost:8000
pytest                          # checks the money maths in assets/pantry.js
ruff check .
python tools/doctor.py          # validates the ledger
```

Opening the files directly with `file://` will not work — the pages fetch the
CSVs, which needs a real HTTP server.

`pytest` runs `assets/pantry.js` inside a JavaScript engine — the code that
actually ships, not a Python reimplementation of it — and checks the arithmetic
against a fixed ledger in `tests/conftest.py`, including that repeated small
amounts do not drift the way float dollars would. The real ledger in `data/` is
checked for consistency rather than for a particular total, so adding a real
contribution never breaks the suite.

---

## Layout

```
index.html              Balance and the three buttons
budget.html             Balance, category breakdown, every transaction
suggestions.html        Embedded form + current suggestions
assets/pantry.js        CSV parsing, money maths, rendering
assets/style.css        Mobile-first styling
data/contributions.csv  Who paid in
data/expenses.csv       What was bought
data/config.json        Form URLs, categories, monthly amount
tools/make_qr.py        QR sticker generator
tools/doctor.py         Ledger validator
tests/test_ledger.py    Money maths tests
tests/test_render.py    Page rendering tests
tests/conftest.py       The fixed ledger the tests assert against
Plan-Office-Pantry.md   Full design document
CLAUDE.md               Working notes for Claude Code
```
