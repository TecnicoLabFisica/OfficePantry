
🥨 Office Pantry

«[!summary] Project
A lightweight web application for managing a shared office snack and supplies fund.

Coworkers contribute a fixed monthly amount, currently $5, which is used to purchase snacks, drinks, and other office supplies.

A single NFC sticker provides access to the application, where coworkers can suggest products, vote on suggestions, see the current budget, and review purchases.»

---

1. Project Goals

The system should:

- Provide a single NFC entry point to the application.
- Allow coworkers to quickly suggest snacks, drinks, and other supplies.
- Allow coworkers to vote on existing suggestions.
- Track the shared office fund.
- Display the current month's balance transparently.
- Maintain a history of expenses.
- Organize expenses by category.
- Track monthly contributions.
- Allow the administrator to record contributions manually.
- Convert an approved purchase directly into an expense.
- Automatically roll the account into a new month.
- Provide a simple notification mechanism for the administrator when new suggestions are available.
- Require authentication for users while keeping the interface simple.

The system should prioritize:

1. Simplicity
2. Transparency
3. Low friction
4. Maintainability
5. Modularity

---

2. Selected Features

Feature| Decision
NFC| One NFC sticker → web application
Landing page| Dashboard + actions
Suggestions| Suggestions + voting + status
Budget| Monthly ledger + categories
Receipts| Not included
Contributions| Administrator records payments
Authentication| User identification + accounts
Purchasing| Purchase automatically creates expense
Monthly accounts| Automatic rollover
Statistics| Not included
Notifications| Administrator notifications
Backend| Python + FastAPI
Database| SQLite

---

3. User Experience

3.1 NFC

The NFC sticker contains only the application's URL.

NFC sticker
     │
     ▼
https://office-pantry.example

The NFC should not contain application data or authentication information.

This allows the sticker to remain unchanged even if the application evolves.

---

3.2 Landing Page

After tapping the NFC, the user reaches the main dashboard.

┌──────────────────────────────────┐
│          🥨 Office Pantry        │
│                                  │
│          August 2026             │
│                                  │
│       Available: $23.60         │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ 💡 Suggest something         │ │
│ └──────────────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ 🗳️ Vote on suggestions       │ │
│ └──────────────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ 💰 Check budget              │ │
│ └──────────────────────────────┘ │
│                                  │
│ ┌──────────────────────────────┐ │
│ │ 🛒 See purchases             │ │
│ └──────────────────────────────┘ │
└──────────────────────────────────┘

The current balance should be immediately visible without requiring navigation.

---

4. User Roles

The application has two conceptual roles.

4.1 Coworker

A coworker can:

- Log in.
- View the current budget.
- View expenses.
- View purchases.
- Submit suggestions.
- View suggestions.
- Vote on suggestions.

A coworker cannot:

- Modify expenses.
- Modify contributions.
- Create purchases.
- Change account balances.
- Modify other users.
- Access administrative functions.

---

4.2 Administrator

The administrator can additionally:

- Manage coworkers.
- Record monthly contributions.
- Create expenses.
- Create purchases.
- Change suggestion status.
- Convert suggestions into purchases.
- Manage monthly accounts.
- Receive notifications.
- Correct erroneous records.

---

5. Authentication

Authentication will use user accounts rather than completely anonymous access.

The initial implementation should prioritize simplicity.

Possible workflow:

NFC
 │
 ▼
Landing page
 │
 ▼
"Log in"
 │
 ▼
User authentication
 │
 ▼
Application

The exact authentication mechanism should be selected during implementation.

Potential options:

- Username + password
- Email + password
- Magic link
- OAuth

For the initial implementation, avoid introducing an external authentication provider unless necessary.

---

6. Suggestions Module

6.1 Creating a Suggestion

A coworker submits:

Product:
[_____________________]

Category:
[ Snacks ▼ ]

[ Submit suggestion ]

Categories initially include:

- 🍪 Snacks
- 🥤 Drinks
- ☕ Coffee
- 💊 Supplements
- 📦 Other

The category list should be configurable later.

---

6.2 Suggestion Lifecycle

Every suggestion has a status.

💡 Suggested
      │
      ▼
🗳️ Voting
      │
      ▼
🛒 To Buy
      │
      ▼
✅ Bought

Possible statuses:

Status| Meaning
"suggested"| Recently submitted
"voting"| Available for voting
"to_buy"| Selected for the next purchase
"bought"| Already purchased
"rejected"| Not going to be purchased

---

7. Voting Module

Coworkers can vote on suggestions.

Example:

Current suggestions

🥜 Mixed nuts       👍 8
🍫 Chocolate        👍 6
🍪 Cookies          👍 4
🧃 Juice            👍 2

The system should prevent a user from voting multiple times on the same suggestion.

The database should therefore associate:

User ←→ Vote ←→ Suggestion

rather than simply storing a vote counter.

This allows the application to enforce:

«One user can vote once per suggestion.»

---

8. Budget Module

The budget page provides a transparent view of the shared fund.

Example:

AUGUST 2026

Contributions
$60.00

Expenses
$36.40

────────────────

Remaining
$23.60

The budget should also provide the expense breakdown.

🍪 Snacks       $14.25
💧 Drinks       $15.65
☕ Coffee        $6.50

---

9. Expense Ledger

Every expense represents money leaving the shared fund.

Example:

August 28

Water + snacks
Drinks
-$14.75

Each expense should contain at minimum:

id
date
description
category
amount
created_by

Receipts are explicitly out of scope for the initial version.

---

10. Contributions Module

The administrator manually records contributions.

Example:

August 2026

Juan       $5.00   ✓
Carlos     $5.00   ✓
Ana        $5.00   ✓
Maria      $5.00   ✓

The system should track:

- coworker
- month
- amount
- date paid
- administrator who recorded it

The expected contribution amount should be configurable rather than hard-coded to "$5".

monthly_contribution = $5.00

This allows the amount to change in the future without changing the application logic.

---

11. Purchasing Module

This module connects suggestions with the financial system.

Example:

Suggestion

🥜 Mixed nuts
8 votes

[ Mark as "To Buy" ]

After purchasing:

Purchase

🥜 Mixed nuts
$7.50

[ Confirm purchase ]

Confirming the purchase should automatically:

1. Create a purchase record.
2. Create the corresponding expense.
3. Associate the expense with the purchase.
4. Change the suggestion status to "bought".

Conceptually:

Suggestion
     │
     ▼
  To Buy
     │
     ▼
  Purchase
     │
     ├──────────► Expense
     │
     ▼
  Bought

This prevents having to enter the same purchase twice.

---

12. Monthly Accounts

The system operates using monthly accounting periods.

Example:

July 2026
────────────
Opening balance
+ Contributions
- Expenses
= Closing balance

        ↓

August 2026
────────────
Opening balance
+ Contributions
- Expenses
= Closing balance

The balance should automatically carry forward.

Formula:

closing_balance =
    opening_balance
    + contributions
    - expenses

Then:

next_month.opening_balance =
    previous_month.closing_balance

---

13. Monthly Rollover

At the beginning of a new month, the application should create the new accounting period.

Example:

July 2026
Closing balance: $12.50

          ↓ rollover

August 2026
Opening balance: $12.50
Contributions:   $60.00
Expenses:        $36.40

Current balance: $36.10

The rollover process should be designed so that it cannot accidentally duplicate money.

Prefer deriving balances from transactions rather than manually editing a balance field.

---

14. Notifications

Notifications are initially intended for the administrator.

The first notification system can be deliberately simple.

Example:

🔔 New suggestions

3 new suggestions have been submitted
since your last visit.

Possible notification events:

- New suggestion
- New vote activity
- Low balance
- New month
- Unrecorded contribution

The initial implementation does not need push notifications.

A notification center inside the admin interface is sufficient.

---

15. Admin Dashboard

The administrator dashboard is the operational center of the application.

Possible layout:

ADMIN DASHBOARD

Current balance
$36.10

────────────────────────

🔔 Notifications
3 new suggestions

────────────────────────

💡 Suggestions
8 active

🛒 To Buy
4 items

💰 Contributions
10 / 12 paid

────────────────────────

Quick actions

[ Add contribution ]
[ Add expense ]
[ Create purchase ]
[ Manage suggestions ]
[ Manage users ]

---

16. Database

The initial database will be:

«SQLite»

The application should access it through:

«SQLAlchemy»

This keeps the application independent of the underlying database implementation.

The conceptual schema is:

User
 │
 ├──── Contribution
 │
 ├──── Suggestion
 │        │
 │        └──── Vote
 │
 ├──── Expense
 │
 └──── Purchase
          │
          └──── Expense

AccountMonth

---

17. Initial Database Entities

User

User
----
id
name
username/email
password_hash
role
active
created_at

---

Contribution

Contribution
------------
id
user_id
account_month_id
amount
paid_at
recorded_by
created_at

---

Suggestion

Suggestion
----------
id
user_id
description
category
status
created_at
updated_at

---

Vote

Vote
----
id
user_id
suggestion_id
created_at

Constraint:

UNIQUE(user_id, suggestion_id)

---

Purchase

Purchase
--------
id
suggestion_id
description
category
amount
purchased_at
created_by

---

Expense

Expense
-------
id
account_month_id
purchase_id
description
category
amount
date
created_by

A purchase-created expense should reference its purchase.

---

AccountMonth

AccountMonth
------------
id
year
month
opening_balance
created_at
closed_at

Constraint:

UNIQUE(year, month)

---

18. Backend Architecture

The backend will use:

«Python + FastAPI + SQLAlchemy + SQLite»

Suggested structure:

office-pantry/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── suggestions.py
│   │   ├── votes.py
│   │   ├── budget.py
│   │   ├── contributions.py
│   │   ├── purchases.py
│   │   └── admin.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── suggestion.py
│   │   ├── vote.py
│   │   ├── contribution.py
│   │   ├── purchase.py
│   │   ├── expense.py
│   │   └── account.py
│   │
│   ├── schemas/
│   │   └── ...
│   │
│   ├── services/
│   │   ├── budget.py
│   │   ├── purchases.py
│   │   ├── suggestions.py
│   │   └── accounts.py
│   │
│   └── database.py
│
├── tests/
│
├── frontend/
│
├── migrations/
│
├── .env
├── .gitignore
├── pyproject.toml
└── README.md

The API layer should remain thin.

Business logic should live primarily in "services/".

---

19. API Modules

The API should be organized around application features.

Example:

/api/auth
/api/suggestions
/api/votes
/api/budget
/api/contributions
/api/purchases
/api/admin

Possible endpoints:

GET    /api/budget/current
GET    /api/budget/expenses

GET    /api/suggestions
POST   /api/suggestions
POST   /api/suggestions/{id}/vote

GET    /api/purchases

POST   /api/admin/contributions
POST   /api/admin/expenses
POST   /api/admin/purchases

POST   /api/admin/suggestions/{id}/status

The exact API design should be refined while implementing the modules.

---

20. Development Phases

Phase 0 — Project Setup

- [ ] Create Git repository
- [ ] Create Python environment
- [ ] Install FastAPI
- [ ] Install SQLAlchemy
- [ ] Configure SQLite
- [ ] Create basic FastAPI application
- [ ] Establish project structure
- [ ] Configure testing
- [ ] Create initial README

---

Phase 1 — Database

- [ ] Define SQLAlchemy models
- [ ] Define relationships
- [ ] Add constraints
- [ ] Configure migrations
- [ ] Create initial database
- [ ] Write database tests

---

Phase 2 — Authentication

- [ ] Create users
- [ ] Implement authentication
- [ ] Implement sessions/tokens
- [ ] Implement roles
- [ ] Protect admin endpoints
- [ ] Create initial admin account

---

Phase 3 — Budget

- [ ] Create monthly accounts
- [ ] Implement contributions
- [ ] Implement expenses
- [ ] Calculate current balance
- [ ] Implement expense categories
- [ ] Implement monthly rollover
- [ ] Add budget API

---

Phase 4 — Suggestions

- [ ] Create suggestions
- [ ] Display suggestions
- [ ] Implement categories
- [ ] Implement statuses
- [ ] Implement voting
- [ ] Prevent duplicate votes
- [ ] Add suggestion API

---

Phase 5 — Purchasing

- [ ] Create purchase workflow
- [ ] Convert suggestion → purchase
- [ ] Automatically create expense
- [ ] Mark suggestion as bought
- [ ] Display purchase history

---

Phase 6 — Frontend

- [ ] Create landing page
- [ ] Create login page
- [ ] Create budget view
- [ ] Create suggestion interface
- [ ] Create voting interface
- [ ] Create purchase history
- [ ] Create admin dashboard

---

Phase 7 — NFC

- [ ] Deploy application
- [ ] Obtain permanent URL
- [ ] Program NFC sticker
- [ ] Test Android NFC
- [ ] Test iPhone NFC
- [ ] Place sticker in office
- [ ] Test complete workflow

---

Phase 8 — Notifications

- [ ] Create notification model
- [ ] Detect new suggestions
- [ ] Detect relevant admin events
- [ ] Create admin notification center
- [ ] Add unread/read state

---

21. MVP Definition

The first usable release should contain:

                🏢 OFFICE PANTRY
                       │
                       ▼
                     NFC
                       │
                       ▼
                 Web application
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Budget       Suggestions       Purchases
        │              │              │
        │              ▼              │
        │            Voting            │
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                    SQLite

MVP must support

- [ ] NFC → application
- [ ] User authentication
- [ ] User accounts
- [ ] Suggestions
- [ ] Voting
- [ ] Suggestion statuses
- [ ] Monthly contributions
- [ ] Expenses
- [ ] Budget calculation
- [ ] Expense categories
- [ ] Purchases
- [ ] Purchase → expense automation
- [ ] Monthly rollover
- [ ] Admin dashboard

Explicitly excluded from MVP

- [ ] Receipt uploads
- [ ] Statistics
- [ ] Charts
- [ ] Push notifications
- [ ] Advanced analytics
- [ ] Multiple NFC stickers
- [ ] External payment integration

---

22. Design Principles

«[!important]
The NFC is the entry point, not the application.»

The application must remain useful even if users access it through a normal URL.

---

«[!important]
Money should be represented by transactions.»

Avoid maintaining a manually editable:

current_balance = $36.10

Instead derive it from:

opening balance
+ contributions
- expenses

This makes the accounting auditable.

---

«[!important]
Purchases and expenses are related but conceptually different.»

A purchase answers:

«What did we buy?»

An expense answers:

«How much money left the fund?»

Usually they correspond one-to-one, but keeping the concepts separate gives us flexibility later.

---

«[!important]
The public interface should be simple.»

A coworker should be able to:

Tap NFC
   ↓
Log in
   ↓
Suggest something
   ↓
Done

in under a minute.

---

23. Future Expansion

These features are intentionally left outside the initial scope.

📊 Statistics

- Spending trends
- Most popular products
- Most purchased products
- Spending by category
- Monthly comparisons

🧾 Receipts

- Receipt images
- Expense evidence
- Receipt archive

🔔 Advanced notifications

- Push notifications
- Email notifications
- Low-balance alerts
- Purchase notifications

🗳️ Advanced voting

- Weighted voting
- Voting deadlines
- Monthly polls
- Automatic selection based on votes

📱 Progressive Web App

Eventually the application could become a PWA:

NFC
 ↓
Web app
 ↓
"Add to home screen"
 ↓
📱 Office Pantry

🏢 Multiple funds

The architecture could eventually support:

Office Pantry
     │
     ├── Snacks
     ├── Coffee
     └── Supplies

or even multiple independent offices/funds.

---

24. Success Criteria

The project is successful when:

1. A coworker can tap the NFC and reach the application.
2. They can authenticate without assistance.
3. They can submit a suggestion in less than one minute.
4. They can vote on suggestions.
5. They can see exactly how much money is available.
6. They can inspect the expense history.
7. The administrator can record monthly contributions.
8. A purchase can automatically become an expense.
9. The monthly account rolls over correctly.
10. The administrator can operate the entire system from the web interface.

---

25. First Implementation Target

The first technical milestone should not be the NFC sticker.

Instead:

FastAPI
   │
   ├── SQLite
   │
   ├── SQLAlchemy
   │
   └── Basic web interface
            │
            ├── Login
            ├── Budget
            ├── Suggestions
            └── Admin

Once the application works locally:

Local application
       ↓
Deploy
       ↓
Permanent URL
       ↓
NFC sticker
       ↓
Real-world testing

This prevents the NFC layer from distracting from the actual application architecture.
