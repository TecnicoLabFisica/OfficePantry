#!/usr/bin/env python3
"""Check the ledger before it reaches the page.

The pages derive every number from data/contributions.csv and data/expenses.csv,
and those files are usually edited through the GitHub web UI where nothing checks
them. A malformed row does not raise an error in the browser -- it shifts the
columns, the amount parses to zero, and the balance is quietly wrong. This script
is what notices.

It also answers the question the admin actually asks every month: who still owes.
data/config.json lists the members who chip in, each with the months they belong
to the fund -- {"name", "from", "to"}, where "to" is the last month they pay for
or "active" -- so nobody is asked for a month before they joined or after they
left. Their rows for the month are added up against monthlyContribution --
payments arrive in parts, so somebody having paid is a total, not the presence of
a row. A member marked "oneTime" gave once and is never asked for more.

    python tools/doctor.py                  # report everything
    python tools/doctor.py --quiet          # errors only, for CI
    python tools/doctor.py --month 2026-08  # ask about a month that has passed

Exit status is 0 when there are no errors, 1 otherwise. Warnings never fail, and
an unpaid contribution is neither -- it is a fact about the month.
"""

import argparse
import csv
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CONTRIBUTIONS_HEADER = ["date", "name", "month", "amount"]
EXPENSES_HEADER = ["date", "description", "category", "amount"]

# Deliberately strict. "5,00", "$5.00" and "5.000" all reach toCents() as
# something, and something is worse than nothing when it is money.
AMOUNT_RE = re.compile(r"^\d+(\.\d{1,2})?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

REQUIRED_CONFIG_KEYS = ["fundName", "monthlyContribution", "currencySymbol",
                        "categories"]

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


class Report:
    """Collects findings so every problem is reported, not just the first."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, message):
        self.errors.append(f"{where}: {message}")

    def warn(self, where, message):
        self.warnings.append(f"{where}: {message}")

    def ok(self):
        return not self.errors


def read_rows(path, report):
    """Parse a ledger CSV the way assets/pantry.js does.

    Blank lines and lines starting with '#' are skipped there, so they are
    skipped here. Returns (header, [(line_number, fields)]) or None.
    """
    if not path.exists():
        report.error(rel(path), "file is missing")
        return None

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        parsed = [(reader.line_num, row) for row in reader]

    kept = [(n, r) for n, r in parsed
            if any(c.strip() for c in r) and not r[0].strip().startswith("#")]
    if not kept:
        report.error(rel(path), "file is empty")
        return None

    header = [c.strip() for c in kept[0][1]]
    return header, kept[1:]


def rel(path):
    return str(pathlib.Path(path).resolve().relative_to(ROOT))


def money(cents, symbol="$"):
    """Integer cents to text, the way assets/pantry.js formats it."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{symbol}{cents // 100}.{cents % 100:02d}"


def month_label(month):                  # "2026-09" -> "September 2026"
    year, mon = month.split("-")
    return f"{MONTHS[int(mon) - 1]} {year}"


def current_month():
    """This month where the office is, not where the clock keeps time.

    UTC runs ahead of here, so on the evening of the last day of a month it has
    already rolled over and would ask about a month nobody has started paying.
    """
    local = datetime.datetime.now(datetime.timezone.utc).astimezone()
    return local.strftime("%Y-%m")


def check_shape(path, header, rows, expected, report):
    """Header and field count. This is the check that catches the comma bug."""
    if header != expected:
        report.error(f"{rel(path)}:1",
                     f"header is {header}, expected {expected}")
        return False

    shape_ok = True
    for line_no, row in rows:
        if len(row) != len(expected):
            report.error(
                f"{rel(path)}:{line_no}",
                f"expected {len(expected)} fields, found {len(row)} "
                "-- quote any description containing a comma, and write "
                "amounts as 5.00 rather than 5,00")
            shape_ok = False
    return shape_ok


def check_date(where, value, report):
    if not DATE_RE.match(value):
        report.error(where, f"date {value!r} is not YYYY-MM-DD")
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        report.error(where, f"date {value!r} is not a real date")
        return None


def check_amount(where, value, report):
    if not AMOUNT_RE.match(value):
        report.error(
            where,
            f"amount {value!r} is not a plain number with at most two decimals "
            "-- the page reads this as $0.00 and the balance goes wrong")
        return 0
    return round(float(value) * 100)


def check_contributions(report):
    """Validates every row. Returns (total_cents, [(line, name, month, cents)]).

    The entries come back because who has paid is a question about several rows
    at once, and the checks that ask it live below.
    """
    path = DATA / "contributions.csv"
    result = read_rows(path, report)
    if result is None:
        return 0, []
    header, rows = result
    if not check_shape(path, header, rows, CONTRIBUTIONS_HEADER, report):
        return 0, []

    total = 0
    entries = []
    for line_no, row in rows:
        where = f"{rel(path)}:{line_no}"
        date_str, name, month, amount = (c.strip() for c in row)

        parsed_date = check_date(where, date_str, report)
        cents = check_amount(where, amount, report)
        total += cents

        if not name:
            report.error(where, "name is empty")
        elif " " in name:
            report.error(
                where,
                f"name {name!r} looks like a full name -- first names only, "
                "this repository is public")

        if not MONTH_RE.match(month):
            report.error(where, f"month {month!r} is not YYYY-MM")
        elif parsed_date and month != date_str[:7]:
            report.error(where,
                         f"month {month!r} does not match date {date_str!r}")

        entries.append((line_no, name, month, cents))

    return total, entries


def check_expenses(report, categories):
    path = DATA / "expenses.csv"
    result = read_rows(path, report)
    if result is None:
        return 0
    header, rows = result
    if not check_shape(path, header, rows, EXPENSES_HEADER, report):
        return 0

    total = 0
    for line_no, row in rows:
        where = f"{rel(path)}:{line_no}"
        date_str, description, category, amount = (c.strip() for c in row)

        check_date(where, date_str, report)
        total += check_amount(where, amount, report)

        if not description:
            report.error(where, "description is empty")

        if category not in categories:
            report.error(
                where,
                f"category {category!r} is not in data/config.json "
                f"({', '.join(sorted(categories))}) -- a typo becomes its own "
                "row in the breakdown instead of failing")

    return total


def check_config(report):
    """Returns the parsed config, or an empty dict if it is unusable."""
    path = DATA / "config.json"
    if not path.exists():
        report.error(rel(path), "file is missing")
        return {}

    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.error(f"{rel(path)}:{exc.lineno}",
                     f"is not valid JSON ({exc.msg}) -- all three pages break")
        return {}

    for key in REQUIRED_CONFIG_KEYS:
        if key not in cfg:
            report.error(rel(path), f"missing required key {key!r}")

    for key in ["suggestionFormUrl", "suggestionSheetCsvUrl"]:
        if not cfg.get(key):
            report.warn(rel(path),
                        f"{key} is empty -- the suggestions page explains "
                        "itself instead of working")

    if not cfg.get("repoUrl"):
        report.warn(rel(path),
                    "repoUrl is empty -- the edit history link on budget.html "
                    "falls back to the URL hardcoded in the page")

    return cfg


def check_members(report, cfg):
    """The monthly roster, as [{name, from, to, oneTime}], or [] when unusable.

    Each member carries the months they belong to the fund. "to" is inclusive --
    the last month they pay for -- or "active" while they still do. Without the
    range, adding somebody in October would have them owing for September and
    every month before it, permanently.
    """
    where = rel(DATA / "config.json")
    members = cfg.get("members")

    if not members:
        report.warn(where, "members is empty -- nobody is checked for the "
                           "monthly contribution")
        return []
    if not isinstance(members, list):
        report.error(where, "members must be a list -- any other shape checks "
                            "nobody and says nothing")
        return []

    roster = []
    seen = set()
    for entry in members:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) \
                or not entry["name"].strip():
            report.error(where,
                         f"member {entry!r} is not an entry -- use "
                         '{"name": "Ana", "from": "YYYY-MM", "to": "active"}')
            continue

        name = entry["name"].strip()
        start, end = entry.get("from"), entry.get("to")
        one_time = entry.get("oneTime", False)
        valid = True
        if not isinstance(start, str) or not MONTH_RE.match(start):
            report.error(where, f"member {name!r} has from {start!r} -- it "
                                "must be the YYYY-MM month they started")
            valid = False
        if end != "active" and (not isinstance(end, str)
                                or not MONTH_RE.match(end)):
            report.error(where, f"member {name!r} has to {end!r} -- it must be "
                                'the last YYYY-MM month they paid, or "active"')
            valid = False
        if valid and end != "active" and end < start:
            report.error(where, f"member {name!r} ends in {end}, before they "
                                f"start in {start}")
        if not isinstance(one_time, bool):
            report.error(where, f"member {name!r} has oneTime {one_time!r} -- "
                                "it must be true or false")
            one_time = False

        if " " in name:
            report.error(where,
                         f"member {name!r} looks like a full name -- first "
                         "names only, this repository is public")
        if name.lower() in seen:
            report.warn(where, f"member {name!r} is listed twice")
        seen.add(name.lower())
        if valid:
            roster.append({"name": name, "from": start, "to": end,
                           "oneTime": one_time})
    return roster


def in_range(member, month):
    """Whether `month` falls inside the months this member belongs to."""
    return member["from"] <= month and (member["to"] == "active"
                                        or month <= member["to"])


def active_members(roster, month):
    """The names expected to pay for `month`, in roster order.

    A one-time contributor gave what they gave and is never expected to pay.
    """
    return [m["name"] for m in roster
            if in_range(m, month) and not m["oneTime"]]


def check_contribution_amount(report, cfg):
    """monthlyContribution as integer cents. 0 when it cannot be used."""
    if "monthlyContribution" not in cfg:
        return 0                          # already reported as missing above
    value = cfg["monthlyContribution"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or value <= 0:
        report.error(rel(DATA / "config.json"),
                     f"monthlyContribution {value!r} is not a positive number "
                     "-- there is nothing to measure a month against")
        return 0
    return round(float(value) * 100)


def month_totals(entries, month):
    """What each name adds up to in one month.

    Payments arrive in parts -- $3.00 now, the other $2.00 next week -- so a
    person's standing for a month is the sum of their rows, never one of them.
    Keyed by lowercased name, carrying the spelling used and the lines it came
    from.
    """
    totals = {}
    for line_no, name, row_month, cents in entries:
        if row_month != month or not name:
            continue
        key = name.lower()
        if key not in totals:
            totals[key] = {"name": name, "cents": 0, "lines": []}
        totals[key]["cents"] += cents
        totals[key]["lines"].append(line_no)
    return totals


def check_overpayments(report, entries, cuota, symbol="$"):
    """A month where somebody's rows add up to more than the contribution.

    This replaces a plain duplicate-row check. Two rows for one person in one
    month is how a split payment is recorded and is exactly right; what is worth
    a second look is the total overshooting -- a payment entered twice, or 50.00
    typed where 5.00 was meant.
    """
    path = DATA / "contributions.csv"
    for month in sorted({m for _, _, m, _ in entries if MONTH_RE.match(m)}):
        for info in month_totals(entries, month).values():
            if info["cents"] <= cuota:
                continue
            lines = ", ".join(str(n) for n in info["lines"])
            report.warn(
                f"{rel(path)}:{info['lines'][-1]}",
                f"{info['name']} adds up to {money(info['cents'], symbol)} for "
                f"{month}, more than the {money(cuota, symbol)} contribution "
                f"(line {lines}) -- add a correcting row if this is a double "
                "entry, never delete one")


def check_unknown_names(report, entries, roster, month):
    """Somebody paying this month who is not on the roster.

    This is the check that catches a typo. 'Cristhopher' reads as one paid-up
    stranger plus one member who never paid, and without the roster only the
    second half of that is visible.

    Deliberately limited to the month being checked: a one-off contributor in a
    month gone by -- somebody handing over the last administration's float -- is
    a permanent row, and a permanent warning nobody can clear is a warning
    everybody learns to scroll past.
    """
    path = DATA / "contributions.csv"
    known = {m["name"].lower() for m in roster}
    for key, info in sorted(month_totals(entries, month).items()):
        if key in known:
            continue
        report.warn(
            f"{rel(path)}:{info['lines'][0]}",
            f"{info['name']} paid for {month} but is not in the members list "
            "in data/config.json -- check the spelling, or add them")


def check_out_of_range(report, entries, roster):
    """A member paying for a month outside the months they belong to the fund.

    Unlike a stranger in a month gone by, this is always fixable -- the row's
    month is wrong, or the roster's from/to is -- so every month is checked.
    """
    path = DATA / "contributions.csv"
    by_name = {m["name"].lower(): m for m in roster}
    for month in sorted({m for _, _, m, _ in entries if MONTH_RE.match(m)}):
        for key, info in sorted(month_totals(entries, month).items()):
            member = by_name.get(key)
            if member is None or in_range(member, month):
                continue
            report.warn(
                f"{rel(path)}:{info['lines'][0]}",
                f"{info['name']} paid for {month} but their membership runs "
                f"{member['from']} to {member['to']} in data/config.json -- "
                "check the row's month, or the member's from/to")


def dues(entries, members, cuota, month):
    """Who still owes for `month`, in roster order, as (name, paid_cents).

    Not errors and not warnings. An unpaid contribution is a fact about the
    month rather than a broken ledger -- on the first of the month everybody is
    on this list and nothing at all is wrong.
    """
    totals = month_totals(entries, month)
    return [(name, totals.get(name.lower(), {}).get("cents", 0))
            for name in members
            if totals.get(name.lower(), {}).get("cents", 0) < cuota]


def print_dues(month, owing, members, cuota, symbol):
    if not members:
        print(f"{month_label(month)} -- nobody on the roster pays for this "
              "month.")
        return
    if not owing:
        print(f"{month_label(month)} -- everyone has paid.")
        return

    outstanding = sum(cuota - paid for _, paid in owing)
    print(f"{month_label(month)} -- {len(members) - len(owing)} of "
          f"{len(members)} paid, {money(outstanding, symbol)} outstanding.")
    width = max(len(name) for name, _ in owing)
    for name, paid in owing:
        state = (f"paid {money(paid, symbol)} of {money(cuota, symbol)}"
                 if paid else "nothing yet")
        print(f"  {name:<{width}}  {state}")


def check_against_pantry_js(report, expected_cents):
    """Re-derive the balance with assets/pantry.js and compare.

    The Python arithmetic above is a second implementation of the money maths.
    Two implementations are only useful if they agree, so ask the one that
    actually ships. Skipped when quickjs is unavailable, so this script still
    runs on a bare python3.
    """
    try:
        import quickjs
    except ImportError:
        return None

    ctx = quickjs.Context()
    ctx.eval("var document={querySelector:function(){return null;}};"
             "var console={error:function(){},log:function(){}};")
    ctx.eval((ROOT / "assets/pantry.js").read_text(encoding="utf-8"))

    contributions = (DATA / "contributions.csv").read_text(encoding="utf-8")
    expenses = (DATA / "expenses.csv").read_text(encoding="utf-8")
    ctx.eval(
        f"var C=Pantry.parseCSV({json.dumps(contributions)});"
        f"var E=Pantry.parseCSV({json.dumps(expenses)});"
        "var L={contributions:C.map(function(r){"
        "  return {cents:Pantry.toCents(r.amount)};}),"
        "       expenses:E.map(function(r){"
        "  return {cents:Pantry.toCents(r.amount)};})};")
    actual = ctx.eval("Pantry.balance(L)")

    if actual != expected_cents:
        report.error(
            "assets/pantry.js",
            f"the page computes a balance of {actual} cents but the ledger "
            f"adds up to {expected_cents} -- the two disagree, so a row is "
            "being read differently than it was written")
    return actual


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true",
                        help="print errors only")
    parser.add_argument("--month", metavar="YYYY-MM",
                        default=current_month(),
                        help="the month to check contributions for "
                             "(default: the current one)")
    args = parser.parse_args(argv)
    if not MONTH_RE.match(args.month) or not 1 <= int(args.month[5:]) <= 12:
        parser.error(f"--month {args.month!r} is not a YYYY-MM month")

    report = Report()
    cfg = check_config(report)
    categories = set(cfg.get("categories", {}))
    roster = check_members(report, cfg)
    cuota = check_contribution_amount(report, cfg)
    symbol = cfg.get("currencySymbol") or "$"

    contributed, entries = check_contributions(report)
    spent = check_expenses(report, categories)

    if cuota:
        check_overpayments(report, entries, cuota, symbol)
    if roster:
        check_unknown_names(report, entries, roster, args.month)
        check_out_of_range(report, entries, roster)

    balance = contributed - spent
    checked_by_js = None
    if report.ok():
        checked_by_js = check_against_pantry_js(report, balance)

    for line in report.errors:
        print(f"error  {line}", file=sys.stderr)
    if not args.quiet:
        for line in report.warnings:
            print(f"warn   {line}")

    if not report.ok():
        print(f"\n{len(report.errors)} error(s), "
              f"{len(report.warnings)} warning(s). The ledger is not safe to "
              "publish.", file=sys.stderr)
        return 1

    if not args.quiet:
        via = "confirmed against assets/pantry.js" if checked_by_js is not None \
            else "quickjs not installed, page arithmetic not cross-checked"
        print(f"\nLedger is clean. Balance {money(balance, symbol)} ({via}).")
        if roster and cuota:
            members = active_members(roster, args.month)
            print()
            print_dues(args.month, dues(entries, members, cuota, args.month),
                       members, cuota, symbol)
        if report.warnings:
            print(f"\n{len(report.warnings)} warning(s) above are open to-do "
                  "items, not failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
