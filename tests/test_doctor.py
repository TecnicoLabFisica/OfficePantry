"""Checks what tools/doctor.py says about the monthly contributions.

doctor.py is the only thing that looks at a ledger edited through the GitHub web
UI, and the roster check is the half of it that reports a fact rather than a
fault: who still owes for the month. The distinction is what these tests hold
still -- an unpaid contribution must never fail the run, and a split payment that
adds up must never look like a duplicate.

Nothing here reads data/ or asks what month it is. doctor.py is pointed at a
throwaway ledger under tmp_path and told which month to check, so the suite says
the same thing in December as it does on the first of the month.
"""

import importlib.util
import json
import shutil

import pytest
from conftest import EXPENSES, ROOT

spec = importlib.util.spec_from_file_location("doctor", ROOT / "tools/doctor.py")
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)

MONTH = "2026-04"                    # the month the tests ask about
OTHER_MONTH = "2026-03"              # one they do not

CONFIG = {
    "fundName": "Test Pantry",
    "monthlyContribution": 5.00,
    "members": ["Alice", "Bob", "Cleo"],
    "currencySymbol": "$",
    "repoUrl": "https://example.invalid/pantry",
    "suggestionFormUrl": "https://example.invalid/form",
    "suggestionSheetCsvUrl": "https://example.invalid/sheet.csv",
    # The keys conftest's EXPENSES uses; an unlisted category is an error.
    "categories": {"coffee": {}, "drinks": {}, "snacks": {}, "other": {}},
}


def contributions(*paid):
    """(name, month, amount) triples as a contributions.csv.

    The date is derived from the month so the two can never disagree, which is a
    separate check and not what any of this is about.
    """
    return "date,name,month,amount\n" + "".join(
        f"{month}-{day:02d},{name},{month},{amount}\n"
        for day, (name, month, amount) in enumerate(paid, start=1))


@pytest.fixture
def doctor_run(tmp_path, capsys, monkeypatch):
    """Point doctor.py at a ledger of the test's own and run it.

    A miniature copy of the project rather than a stubbed DATA: doctor.py reports
    paths relative to ROOT and cross-checks its arithmetic against the real
    assets/pantry.js, and both of those are worth keeping in the test.
    """
    shutil.copytree(ROOT / "assets", tmp_path / "assets")
    data = tmp_path / "data"
    data.mkdir()
    (data / "expenses.csv").write_text(EXPENSES)
    monkeypatch.setattr(doctor, "ROOT", tmp_path)
    monkeypatch.setattr(doctor, "DATA", data)

    def run(rows, month=MONTH, **config):
        (data / "contributions.csv").write_text(rows)
        (data / "config.json").write_text(json.dumps(dict(CONFIG, **config)))
        code = doctor.main(["--month", month])
        out, err = capsys.readouterr()
        return code, out + err

    return run


def test_a_member_who_has_not_paid_is_named(doctor_run):
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00"),
                                         ("Bob", MONTH, "5.00")))
    assert code == 0                          # owing money is not a broken file
    assert "2 of 3 paid, $5.00 outstanding" in out
    assert "Cleo" in out and "nothing yet" in out


def test_a_partial_payment_reports_what_is_left(doctor_run):
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00"),
                                         ("Bob", MONTH, "5.00"),
                                         ("Cleo", MONTH, "3.00")))
    assert code == 0
    assert "2 of 3 paid, $2.00 outstanding" in out
    assert "paid $3.00 of $5.00" in out


def test_two_rows_that_add_up_are_a_paid_contribution(doctor_run):
    """The reason the duplicate-row warning had to go.

    Paying $3.00 now and $2.00 next week is how the money actually arrives, and
    a tool that grumbles about the correct way to record it is a tool people
    stop reading.
    """
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00"),
                                         ("Bob", MONTH, "5.00"),
                                         ("Cleo", MONTH, "3.00"),
                                         ("Cleo", MONTH, "2.00")))
    assert code == 0
    assert "everyone has paid" in out
    assert "warn" not in out


def test_rows_adding_up_to_more_than_the_contribution_warn(doctor_run):
    """What a payment entered twice looks like from outside."""
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00"),
                                         ("Bob", MONTH, "5.00"),
                                         ("Cleo", MONTH, "5.00"),
                                         ("Cleo", MONTH, "5.00")))
    assert code == 0
    assert "Cleo adds up to $10.00" in out
    assert "more than the $5.00 contribution" in out


def test_a_payer_who_is_not_on_the_roster_warns(doctor_run):
    """The shape of a misspelt name: a stranger who paid, and a member who
    did not."""
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00"),
                                         ("Bob", MONTH, "5.00"),
                                         ("Cleo", MONTH, "5.00"),
                                         ("Dana", MONTH, "5.00")))
    assert code == 0
    assert "Dana paid for 2026-04 but is not in the members list" in out


def test_a_one_off_contributor_in_another_month_is_left_alone(doctor_run):
    """Somebody handing over the last administration's float is a permanent row.

    Warning about it every run forever would teach everyone to skip warnings, so
    the roster is only held against the month being asked about.
    """
    code, out = doctor_run(contributions(("Dana", OTHER_MONTH, "3.00"),
                                         ("Alice", MONTH, "5.00"),
                                         ("Bob", MONTH, "5.00"),
                                         ("Cleo", MONTH, "5.00")))
    assert code == 0
    assert "Dana" not in out
    assert "everyone has paid" in out


def test_an_empty_roster_warns_and_checks_nobody(doctor_run):
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00")), members=[])
    assert code == 0
    assert "members is empty" in out
    assert "paid" not in out.split("Ledger is clean")[1]


def test_a_full_name_on_the_roster_is_an_error(doctor_run):
    """Same rule as the ledger itself. The repository is public."""
    code, out = doctor_run(contributions(("Alice", MONTH, "5.00")),
                           members=["Alice Fernandez"])
    assert code == 1
    assert "first names only" in out


def test_the_month_asked_about_is_the_month_reported(doctor_run):
    """A past month can be asked about, which is also what keeps this suite from
    depending on the day it runs."""
    code, out = doctor_run(contributions(("Alice", OTHER_MONTH, "5.00")),
                           month=OTHER_MONTH)
    assert code == 0
    assert "March 2026 -- 1 of 3 paid" in out
