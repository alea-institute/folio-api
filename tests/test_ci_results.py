"""The CI report gate must never turn skipped or broken verification green."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_pytest_results import check_report


def _suite(cases='<testcase name="passed"/>', **counts):
    totals = {"tests": "1", "failures": "0", "errors": "0", "skipped": "0", **counts}
    attrs = " ".join(f'{key}="{value}"' for key, value in totals.items())
    return f"<testsuite {attrs}>{cases}</testsuite>"


@pytest.mark.parametrize("wrapped", [False, True])
def test_accepts_passing_pytest_report(tmp_path, wrapped):
    report = tmp_path / "pytest.xml"
    text = _suite()
    report.write_text(f"<testsuites>{text}</testsuites>" if wrapped else text)
    assert check_report(report) == 1


def test_suite_container_totals_are_not_double_counted(tmp_path):
    report = tmp_path / "pytest.xml"
    report.write_text(f'<testsuites tests="2">{_suite()}{_suite()}</testsuites>')
    assert check_report(report) == 2


@pytest.mark.parametrize(
    "text",
    [
        "not XML",
        "<testsuites>",
        "<testsuites/>",
        "<unrelated><testcase/></unrelated>",
        _suite("", tests="0"),
        _suite(tests="0"),
        _suite(tests="not-a-number"),
        _suite(skipped="-1"),
        '<testsuite><testcase name="missing-counters"/></testsuite>',
        _suite("<testcase><skipped/></testcase>", skipped="1"),
        _suite('<testcase><skipped type="pytest.xfail"/></testcase>', skipped="1"),
        _suite("<testcase><failure/></testcase>", failures="1"),
        _suite('<testcase><error message="setup failed"/></testcase>', errors="1"),
        _suite('<testcase><error message="teardown failed"/></testcase>', errors="1"),
        # Neither inaccurate totals nor missing outcome nodes may hide a failure.
        _suite("<testcase><skipped/></testcase>"),
        _suite(failures="1"),
        '<testsuites errors="1">' + _suite() + "</testsuites>",
        # Pytest can emit two records for one call + teardown failure.
        _suite(
            '<testcase name="same"><failure/></testcase>'
            '<testcase name="same"><error/></testcase>',
            failures="1",
            errors="1",
        ),
    ],
)
def test_rejects_incomplete_or_unsuccessful_reports(tmp_path, text):
    report = tmp_path / "pytest.xml"
    report.write_text(text)
    with pytest.raises(ValueError):
        check_report(report)


def test_missing_report_fails(tmp_path):
    with pytest.raises(ValueError, match="Cannot read pytest report"):
        check_report(tmp_path / "absent.xml")


@pytest.mark.parametrize("passing", [False, True])
def test_command_exit_status(tmp_path, passing):
    report = tmp_path / "pytest.xml"
    report.write_text(_suite() if passing else _suite(skipped="1"))
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_pytest_results.py"
    result = subprocess.run(
        [sys.executable, str(script), str(report)], capture_output=True, text=True
    )
    assert result.returncode == (0 if passing else 1)
    assert (
        ("testcase records" in result.stdout)
        if passing
        else ("rejected" in result.stderr)
    )
