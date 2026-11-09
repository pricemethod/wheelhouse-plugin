#!/usr/bin/env python3
"""Prove an edit to a growing file only added things. Standard library only; reads two files and changes nothing.

Usage:  python3 -I append_only.py BEFORE AFTER [--log | --feature-plan]

--log           (BUILD_LOG.md) AFTER must be BEFORE with new text added at the end, and nothing else.
--feature-plan  (FEATURE_PLAN.md) every line of BEFORE must still be in AFTER, in the same order; new lines may be added
                anywhere (a new index row, a scope decision, a backlog item, a new feature at the end). The only line that may
                change in place is a feature's row in the index, and only its Status cell.
Exit code 1 (with the offending lines) if the rule is broken.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

INDEX_ROW = re.compile(r"^\|\s*(\d+)\s*\|(.*)\|(.*)\|(.*)\|\s*$")


def check_log(before: str, after: str) -> list[str]:
    if after.startswith(before):
        return []
    common = 0
    for a, b in zip(before.splitlines(), after.splitlines()):
        if a != b:
            break
        common += 1
    return [f"the log was changed, not just added to (first difference at line {common + 1}); earlier entries must never be edited"]


def _same_except_status(old: str, new: str) -> bool:
    mo, mn = INDEX_ROW.match(old), INDEX_ROW.match(new)
    return bool(mo and mn and mo.group(1) == mn.group(1) and mo.group(2) == mn.group(2) and mo.group(3) == mn.group(3))


def check_feature_plan(before: str, after: str) -> list[str]:
    old, new = before.splitlines(), after.splitlines()
    problems, j = [], 0
    for i, line in enumerate(old, 1):
        k = j
        while k < len(new) and new[k] != line and not _same_except_status(line, new[k]):
            k += 1
        if k == len(new):
            problems.append(f"line {i} of the earlier version was deleted, reworded or moved: {line.strip()[:90]!r}")
            continue
        j = k + 1
    return problems


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2 or not ({"--log", "--feature-plan"} & set(argv)):
        print(__doc__)
        return 2
    before, after = (Path(a).read_text(encoding="utf-8") for a in args)
    problems = check_log(before, after) if "--log" in argv else check_feature_plan(before, after)
    for p in problems:
        print("NOT APPEND-ONLY:", p)
    print("ok: only additions" if not problems else f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
