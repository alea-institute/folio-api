"""Reject empty, malformed or unsuccessful pytest JUnit reports.

This supplements a successful full-suite pytest exit; a partial report cannot
prove completion. Keep pytest and this checker as separate failing CI steps.
"""

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree


def check_report(path: Path) -> int:
    """Return testcase record count (not a claim about unique test identities)."""
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as exc:
        raise ValueError(f"Cannot read pytest report: {exc}") from exc

    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Expected a pytest testsuite or testsuites document")
    suites = list(root.iter("testsuite"))
    cases = list(root.iter("testcase"))
    if not suites or not cases:
        raise ValueError("Pytest report is empty")

    for suite in suites:
        if not {"tests", "failures", "errors", "skipped"} <= suite.attrib.keys():
            raise ValueError("Pytest suite is missing outcome totals")
    # Inspect aggregate totals too, but never add them to per-suite totals.
    for suite in root.iter():
        if suite.tag not in {"testsuite", "testsuites"}:
            continue
        for key in ("tests", "failures", "errors", "skipped"):
            if key not in suite.attrib:
                continue
            try:
                count = int(suite.attrib[key])
            except ValueError as exc:
                raise ValueError(f"Invalid pytest {key} total") from exc
            if count < 0 or (key == "tests" and count == 0):
                raise ValueError(f"Invalid pytest {key} total: {count}")
            if key != "tests" and count:
                raise ValueError(f"Pytest reported {count} {key}")
    if any(node.tag in {"skipped", "failure", "error"} for node in root.iter()):
        raise ValueError("Pytest report contains skipped, failed or errored assertions")
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        count = check_report(args.report)
    except ValueError as exc:
        print(f"Pytest report rejected: {exc}", file=sys.stderr)
        return 1
    print(
        f"Pytest report accepted: {count} testcase records; no skips, failures or errors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
