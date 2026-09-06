🥨 Office Pantry

«[!summary] Project
A shared office snack and supplies fund, run entirely from a static web page.

Coworkers contribute a fixed monthly amount, currently $5, which is used to buy
snacks, drinks, and other office supplies.

A single QR sticker opens the page, where coworkers can see the current balance,
review every transaction, and suggest what to buy next.»

---

0. Revision Note

«[!important]
This document replaced an earlier design built on FastAPI, SQLAlchemy, SQLite,
user accounts, and an NFC sticker.

No code from that design was ever written, so nothing was lost.»

The change had one cause: there is no server to host an application on, and no
appetite for maintaining one. Rather than shrink the old design, the project was
rebuilt around that constraint.

The constraint turned out to remove more work than it added:

Removed| Reason
Authentication, users, passwords| Reading is public; the only write is a form
Database, ORM, migrations| Two CSV files
Backend, API layer| Nothing to serve
Monthly rollover logic| Balances sum every month at once
Voting| Deferred; the admin picks from the list
Notification system| Google Forms already emails on each response

What survived is the principle that mattered: money is represented by
transactions, never by a stored balance.

---

1. Project Goals

The system should:

- Provide a single QR entry point.
- Let coworkers suggest snacks, drinks, and supplies without logging in.
- Display the current balance transparently.
- Show a complete, auditable history of contributions and expenses.
- Organize expenses by category.
- Cost nothing to host and require no maintenance.

The system should prioritize:

1. Simplicity
2. Transparency
3. Low friction
4. Maintainability

---

2. Selected Features

Feature| Decision
Entry point| One QR sticker → static web page
Hosting| GitHub Pages, public repository
Landing page| Balance + three actions
Suggestions| Google Form, no login
Voting| Not in the first version
Budget| Transaction ledger + category breakdown
Contributions| Administrator records them as CSV rows
Authentication| None
Receipts| Not included
Statistics| Not included
Data store| CSV files in the repository
Audit trail| Git history

---

3. Architecture

The system splits along a single line: what can be read, and what must be
written.

┌──────────────┐
│  QR sticker  │
└──────┬───────┘
       ▼
┌──────────────────────┐        ┌──────────────────┐
│     index.html       │───────►│   Google Form    │
│  balance + actions   │        │   (no login)     │
└──┬────────────────┬──┘        └────────┬─────────┘
   │                │                    ▼
   │                │           ┌──────────────────┐
   │                └──────────►│  Google Sheet    │
   │                            │  published CSV   │
   │  suggestions.html ◄────────┘                  │
   │                            └──────────────────┘
   ▼
┌──────────────────────┐
│     budget.html      │
└──────────┬───────────┘
           ▼
┌──────────────────────────────┐
│  data/contributions.csv      │
│  data/expenses.csv           │
│  (admin edits; git = audit)  │
└──────────────────────────────┘

«[!important]
GitHub Pages serves files. It cannot receive a submission.»

This is the constraint that shapes everything. Every write must land somewhere
that is not GitHub Pages:

Write| Destination
A suggestion| Google Form
A contribution| CSV row, committed
An expense| CSV row, committed

---

4. The QR Entry Point

The QR code contains only the site URL.

QR sticker
     │
     ▼
https://tecnicolabfisica.github.io/OfficePantry/

«[!important]
The QR is the entry point, not the application.»

It holds no data and no authentication. The sticker stays valid however the site
evolves, and the page remains perfectly usable typed in by hand.

QR was chosen over NFC because it needs no programming, works from any phone
camera, and costs nothing to reprint.

---

5. Landing Page

┌──────────────────────────────────┐
│          🥨 Office Pantry        │
│                                  │
│          September 2026          │
│                                  │
│           Available              │
│             $9.15                │
│      $7.60 spent this month      │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ 💡 Suggest something         │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ 📋 See suggestions           │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ 💰 Check the money           │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘

The balance is visible immediately, without navigation and without logging in.

---

6. Suggestions

A coworker taps «Suggest something» and reaches an embedded Google Form.

Product:
[_____________________]

Category:
[ Snacks ▼ ]

[ Submit ]

No account, no password, no app. The administrator receives an email for each
response.

Categories:

- 🍪 Snacks
- 💧 Drinks
- ☕ Coffee
- 💊 Supplements
- 📦 Other

The list is configurable in "data/config.json".

Submitted suggestions are read back from the sheet's published CSV and listed
below the form.

«[!important]
The live list is the one part of the system outside this repository's control.»

If Google's published CSV cannot be fetched, the page shows a short message and
the form above keeps working. The feature degrades; nothing breaks.

---

7. Voting

Voting is deliberately absent from the first version.

Without accounts there is no way to prevent someone voting twice, and adding
accounts would reintroduce the entire authentication layer this design exists to
avoid.

For now the administrator chooses from the suggestion list.

If voting is wanted later, the natural form is a monthly poll — «pick your top
three» — as a second Google Form. It needs no change to anything else.

---

8. The Money

Two CSV files hold every transaction.

data/contributions.csv

date,name,month,amount
2026-09-01,Juan,2026-09,5.00

data/expenses.csv

date,description,category,amount
2026-09-03,Mixed nuts,snacks,7.50

«[!important]
Money is represented by transactions.»

There is no "current_balance" field anywhere. The browser derives it on every
page load:

balance = Σ contributions − Σ expenses

---

9. No Monthly Rollover

The earlier design carried a closing balance forward into each new month.

That machinery is gone. Because the balance sums every transaction ever
recorded, the month boundary is not an event:

- Nothing happens on the first of the month.
- No opening balance is written anywhere.
- Money cannot be double-counted by a rollover running twice.

A month is a filter over the data, not a record in it.

---

10. Money Is Counted In Cents

«[!important]
Amounts become integer cents the moment they are parsed, and stay integers
until they are displayed.»

Summing float dollars drifts:

0.10 + 0.20 + 0.10 + 0.10  ≠  0.50

This page exists to be trusted about other people's money, so this is the one
place a subtle bug would do real damage. It is covered by a test.

---

11. Budget Page

AVAILABLE
$9.15

This month
Contributions in     +$20.00
Spent                -$7.60
Net this month       +$12.40

Where the money has gone
💧 Drinks        $14.75
☕ Coffee         $8.50
🍪 Snacks         $7.50
📦 Other          $0.10

Every transaction
September 4   Bag clips        -$0.10
September 3   Mixed nuts       -$7.50
September 3   Maria paid in    +$5.00
...

Every figure on this page is computed from the rows beneath it.

---

12. Transparency and the Audit Trail

The ledger is a set of text files under version control. Every change is a
commit: who changed it, when, and exactly which numbers moved.

«[!important]
Corrections are made by adding a row, never by editing a past one.»

This is stronger than the database design it replaced. A spreadsheet cell can be
silently overwritten; a committed row cannot.

---

13. Privacy

GitHub Pages publishes from a public repository on the free plan, so the ledger
is readable by anyone.

«[!important]
First names only. No surnames, no contact details.»

"Juan paid in $5.00" is meaningful to the four people who share the fund and
useless to anyone else.

---

14. Repository Layout

office-pantry/
│
├── index.html              Balance + three actions
├── budget.html             Balance, breakdown, full history
├── suggestions.html        Embedded form + suggestion list
│
├── assets/
│   ├── style.css           Mobile-first
│   └── pantry.js           CSV parsing, money maths, rendering
│
├── data/
│   ├── contributions.csv
│   ├── expenses.csv
│   └── config.json         Form URLs, categories, monthly amount
│
├── tools/
│   └── make_qr.py          QR sticker generator
│
├── tests/
│   └── test_ledger.py      Money maths, run against pantry.js
│
├── .nojekyll               GitHub Pages serves the files as written
├── environment.yaml
└── README.md

No build step, no framework, no dependencies in the browser.

---

15. Testing

The site needs nothing installed to run. The tests exist for one reason: the
arithmetic handles other people's money.

"tests/test_ledger.py" runs "assets/pantry.js" inside a JavaScript engine and
checks:

- Amounts parse to exact integer cents.
- Formatting is correct across zero, negatives, and thousands.
- CSV descriptions containing commas survive parsing.
- The balance matches a hand-computed total of the real ledger.
- Repeated small amounts do not drift.

Testing the real source, rather than a Python reimplementation of it, is the
point.

---

16. Success Criteria

The project is successful when:

1. A coworker can scan the QR and reach the page.
2. They see the available balance without logging in.
3. They can submit a suggestion in under a minute.
4. They can inspect every transaction that has ever occurred.
5. The administrator can record a contribution or expense in one commit.
6. A new month requires no action from anyone.
7. Hosting costs nothing and requires no maintenance.

---

17. Future Expansion

Left deliberately outside the current scope:

🗳️ Voting
- A monthly «pick your top three» form

🧾 Receipts
- Photographs linked to expense rows

📊 Statistics
- Spending trends, most-requested products

📱 Progressive Web App
- «Add to home screen»

If the ledger ever outgrows hand-edited CSV, the next step is a Google Apps
Script endpoint to append rows — still with no server to run.
