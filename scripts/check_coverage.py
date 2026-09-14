#!/usr/bin/env python3
"""Enforce the "coverage must not decrease" policy.

Runs pytest with coverage over src/ and scripts/, compares against the floor in
coverage-baseline.json, and exits 1 if coverage dropped below it.

Two modes, because integration tests need the owner's local Anki collection, which
a fresh checkout does not have:

  (default) : `pytest -m "not integration"` — what any checkout can run, checked
              against unit_min_percent.
  --full    : the complete suite, checked against full_min_percent. Skips with a
              warning rather than failing when the collection is absent, since a
              suite with every integration test skipped reports a misleadingly low
              number, not a real regression.

Usage:
    python scripts/check_coverage.py
    python scripts/check_coverage.py --full
    python scripts/check_coverage.py --update-baseline
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_BASELINE_FILE = _REPO / "coverage-baseline.json"
_COV_SOURCES = ["src/hebrew_cards", "scripts"]
_COLLECTION = (
    Path.home() / "Library" / "Application Support" / "Anki2" / "User 1" / "collection.anki2"
)

# A drop this small is line-count rounding noise, not a regression.
_TOLERANCE = 0.1


def _run_coverage(full: bool) -> float:
    json_out = _REPO / f"coverage-{'full' if full else 'unit'}.json"
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    if not full:
        cmd += ["-m", "not integration"]
    for src in _COV_SOURCES:
        cmd += [f"--cov={src}"]
    cmd += ["--cov-report=term", f"--cov-report=json:{json_out}", "-q"]
    result = subprocess.run(cmd, cwd=_REPO, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print("tests failed — coverage not evaluated", file=sys.stderr)
        raise SystemExit(result.returncode)

    # A skipped test in unit mode means this environment ran something CI cannot, or
    # vice versa — the usual cause being a test guarded on the owner's local Anki
    # collection. That silently measures a floor CI can never reach, which failed a
    # PR once already. Integration tests are excluded from this mode entirely, so a
    # skip here is worth surfacing rather than a normal occurrence.
    if not full and " skipped" in result.stdout:
        print(
            "\nWARNING: a test skipped during a unit-mode run. If it skipped because "
            "local data was present or absent, this measurement will not match CI.",
            file=sys.stderr,
        )
    with open(json_out) as fh:
        data = json.load(fh)
    percent: float = data["totals"]["percent_covered"]
    return percent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--reason", help="why a floor is being lowered (required when it is)")
    args = parser.parse_args()

    if args.full and not _COLLECTION.exists():
        print("WARNING: no local Anki collection — skipping --full measurement")
        return 0

    key = "full_min_percent" if args.full else "unit_min_percent"
    measured = _run_coverage(args.full)
    baseline = json.loads(_BASELINE_FILE.read_text())

    if args.update_baseline:
        previous = baseline.get(key)
        new = round(measured, 2)
        lowering = previous is not None and new < previous
        if lowering and not args.reason:
            print(
                f"REFUSING: this would lower {key} from {previous} to {new}.\n"
                "The policy requires a lowered floor to state its cause — a ratchet that\n"
                "drifts down unremarked is not a ratchet. Re-run with:\n"
                f'  --update-baseline --reason "why coverage legitimately dropped"',
                file=sys.stderr,
            )
            return 1
        baseline[key] = new
        if args.reason:
            direction = "lowered" if lowering else "raised"
            stamp = f"{key} {direction} {previous} -> {new}: {args.reason}"
            baseline["notes"] = f"{stamp}\n\n{baseline.get('notes', '')}".strip()
        baseline["updated"] = date.today().isoformat()
        _BASELINE_FILE.write_text(json.dumps(baseline, indent=2) + "\n")
        print(f"{key}: {previous} -> {new}")
        return 0

    floor = baseline[key]
    print(f"\n{key}: measured {measured:.2f}%, floor {floor:.2f}%")
    if measured < floor - _TOLERANCE:
        print(f"FAIL: coverage dropped {floor - measured:.2f} points below the floor")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
