---
tags: [office-pantry, status]
date: 2026-09-05
status: awaiting-user-action
---

# 🥨 Office Pantry — Status

The site is built and tested. What remains is yours: the repository has to be public before anything can be published.

Full design: [[Plan-Office-Pantry]]

---

## Session log — 2026-09-05

> [!done] Re-platformed from FastAPI + NFC to a static site + QR
> The old design needed a server. This one is HTML, CSS, two CSV files, and about 150 lines of vanilla JavaScript. No accounts, no database, no backend, no rollover logic — all of it deleted rather than shrunk.

| Area | Files |
| --- | --- |
| Pages | `index.html`, `budget.html`, `suggestions.html` |
| Assets | `assets/pantry.js`, `assets/style.css` |
| Data | `data/contributions.csv`, `data/expenses.csv`, `data/config.json` |
| Tooling | `tools/make_qr.py`, `qr/` output |
| Tests | `tests/test_ledger.py`, `tests/test_render.py` |
| Docs | `README.md`, rewritten [[Plan-Office-Pantry]], slimmed `environment.yaml` |

### What was verified

- **25 tests pass.** `tests/test_ledger.py` runs the real `assets/pantry.js` inside a JavaScript engine (quickjs), not a Python reimplementation of it — so the tests cover the code that actually ships.
- **The balance is right.** $40.00 in − $30.85 out = **$9.15**, hand-computed and matching what the page renders.
- **Float drift is caught.** The `0.10` expense row exists on purpose; a test asserts that repeated small amounts sum exactly.
- **The QR decodes** back to `https://tecnicolabfisica.github.io/OfficePantry/`.
- `ruff` clean, and all eight site assets served HTTP 200 from a local server.

> [!warning] Two things were *not* verified
> - **No browser check.** The Chrome extension is not set up in this session, so the render tests cover the logic — not how the pages actually look on a screen.
> - **Nothing is committed.** All of the above is untracked or modified in the working tree.

---

## Your tasks

> [!todo] In order — the first one blocks everything else
> - [x] **Make the repository public.** `TecnicoLabFisica/OfficePantry` currently returns 404 unauthenticated. GitHub Pages will not publish from a private repository on the free plan. *Settings → General → Change visibility → Public.*
>       This is also what makes the *first names only* rule load-bearing — worth deciding deliberately rather than by default.
> - [x] **Enable Pages.** *Settings → Pages → `main` / root.*
> - [x] **Create the Google Form and its response sheet.** Paste the prompt in
>       [[Prompt-Office-Pantry-Form]] into Gemini and run the script it gives back. It
>       pins the two question titles and the five category options that `assets/pantry.js`
>       matches on — get one wrong and the list renders blank with no error. Two fields
>       only: the first-name field is dropped, because the page never shows it and the
>       response CSV is public.
> - [x] **Publish the response sheet.** *File → Share → Publish to web → CSV.* The one
>       step Apps Script cannot do; the published URL has to be copied by hand.
> - [x] **Fill the two empty strings** in `data/config.json`: `suggestionFormUrl` and `suggestionSheetCsvUrl`. Until then the suggestions page explains itself instead of breaking.
> - [x] **Replace the seed ledger.** The Juan / Carlos / Ana / Maria rows are examples. Real data goes in the same shape — see *Admin: recording money* in `README.md`.
> - [ ] **Print the QR.** `python tools/make_qr.py --url <pages-url>`, then print `qr/print.html`.
> - [ ] **Test on a phone.** Scan, read the balance, submit a suggestion, confirm both the sheet row and the notification email.
> - [ ] **Cold read.** Hand the phone to someone who has never seen it. A suggestion in under a minute, unassisted.
> - [ ] **Decide whether to commit** the working tree.

---

## Two rules worth remembering

> [!info]
> - **Corrections are made by adding a row, never by editing a past one.** Git history is the audit trail; that only holds if past rows stay put.
> - **First names only** in the CSVs. The repository is public.

---

## Known loose end

The *edit history* link on `budget.html` points at the commit history of `data/` on GitHub. It is the transparency promise the whole design leans on — and it will 404 for your coworkers until the repository is public.
