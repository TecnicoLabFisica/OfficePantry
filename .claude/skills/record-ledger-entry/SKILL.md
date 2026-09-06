---
name: record-ledger-entry
description: Use when recording money in Office Pantry — someone paid their monthly contribution, something was bought for the pantry, or a past entry needs correcting. Covers the CSV format rules that silently corrupt the balance when broken.
---

# Recording money

Two files, append-only in spirit. Both live in `data/`.

## Someone paid

Append to `data/contributions.csv`:

```csv
2026-09-14,Ana,2026-09,5.00
```

`date,name,month,amount`. `month` must equal the first seven characters of `date`.

## Something was bought

Append to `data/expenses.csv`:

```csv
2026-09-14,Coffee beans,coffee,8.50
```

`date,description,category,amount`. `category` must be a key in `data/config.json`
(`snacks`, `drinks`, `coffee`, `supplements`, `other`).

## The rules that matter

1. **First names only.** The repository is public.
2. **Quote any description with a comma**: `"Water, snacks"`. Unquoted, the row gains a
   field, `amount` reads as `"drinks"`, `toCents` returns `0`, and the expense vanishes
   from the page with no error at all.
3. **Amounts are plain numbers.** `5.00` — never `$5.00`, never `5,00`, never `5.005`.
4. **Dates are `YYYY-MM-DD`.** Sorting and month bucketing are string operations.
5. **Append. Never edit or delete a past row.** To correct a mistake, add a row that
   cancels it — a negative-signed correction expense, or a compensating contribution —
   and say so in the description. The commit history of `data/` is the audit trail the
   site advertises on `budget.html`.

## Then

```bash
python tools/doctor.py
```

Exit 0 means the ledger is publishable. Fix anything it reports before committing.
Commit the CSV change on its own, with a message naming what was recorded, so the
history reads as a ledger. The live page updates within a minute.
