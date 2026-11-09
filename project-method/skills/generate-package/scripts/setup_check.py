#!/usr/bin/env python3
"""Is this folder ready to hold a project? Standard library only; reads and never changes anything.

Usage:  python3 -I setup_check.py PROJECT_FOLDER [--json]

Used by the `get-ready` skill before a project starts (and as a quick check in later sessions). It reports whether the folder
exists and can be written to, what is already in it (nothing, an interview in progress, a project package, or unrelated files),
whether it is a place a project should not live (the home folder, the whole Desktop, Documents or Downloads), whether it syncs
to the cloud, and whether this Python can run the plugin's other helpers. It never creates, moves or deletes anything.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PACKAGE = {"START-HERE.md", "PROJECT_BRIEF.md", "CLAUDE.md", "PLAN.md", "BUILD_LOG.md", "FEATURE_PLAN.md", "SAFETY.md"}
TOO_BROAD = ("Desktop", "Documents", "Downloads")
CLOUD_MARKS = ("Mobile Documents", "iCloud", "Dropbox", "OneDrive", "Google Drive", "GoogleDrive", "CloudStorage", "Box Sync")
MIN_PYTHON = (3, 9)


def check(folder: Path, home: Path | None = None) -> dict:
    folder = Path(folder).expanduser()
    home = Path(home or Path.home())
    out: dict = {"folder": str(folder), "problems": [], "notes": []}
    out["python_ok"] = sys.version_info[:2] >= MIN_PYTHON
    out["python"] = ".".join(map(str, sys.version_info[:3]))
    if not out["python_ok"]:
        out["notes"].append(f"This Python ({out['python']}) is older than 3.9, so the helper checks will be done by hand instead. Nothing needs installing.")
    if not folder.exists():
        out["exists"] = False
        out["problems"].append("The folder does not exist yet. Create it (or choose another) before starting.")
        return out
    out["exists"] = True
    if not folder.is_dir():
        out["problems"].append("That is a file, not a folder.")
        return out
    out["writable"] = os.access(folder, os.W_OK)
    if not out["writable"]:
        out["problems"].append("Claude cannot save files in this folder. Choose a folder you own, such as a new one inside your Documents.")
    resolved = folder.resolve()
    if resolved == home.resolve():
        out["problems"].append("This is your whole home folder. Make a new folder just for this project.")
    elif resolved.parent == home.resolve() and resolved.name in TOO_BROAD:
        out["problems"].append(f"This is your whole {resolved.name} folder. Make a new folder inside it just for this project.")
    if any(mark in str(resolved) for mark in CLOUD_MARKS):
        out["notes"].append("This folder syncs to the cloud. That is fine (it keeps a backup), but avoid editing the project from two computers at once.")
    names = {p.name for p in folder.iterdir() if not p.name.startswith(".")}
    project_files = names & PACKAGE
    brief = folder / "PROJECT_BRIEF.md"
    if not names:
        out["state"] = "empty"
    elif brief.is_file() and "Interview progress" in brief.read_text(encoding="utf-8", errors="replace"):
        out["state"] = "interview-in-progress"
    elif {"PLAN.md", "BUILD_LOG.md"} <= names:
        out["state"] = "project"
    elif project_files:
        out["state"] = "partial-project"
        out["notes"].append(f"Some project files are here ({', '.join(sorted(project_files))}) but not a complete package.")
    else:
        out["state"] = "other-files"
    others = sorted(n for n in names - PACKAGE if not n.startswith("~"))
    out["other_files"] = others[:10]
    if out["state"] in ("other-files",) or (out["state"] in ("project", "interview-in-progress", "partial-project") and len(others) > 20):
        out["notes"].append("There are other files in this folder. A project works best in its own folder; files you add for the project (a spreadsheet, a document) are fine.")
    out["ready"] = not out["problems"]
    return out


def as_text(r: dict) -> str:
    lines = [f"Folder: {r['folder']}"]
    if r.get("exists"):
        lines.append(f"Can save files here: {'yes' if r.get('writable') else 'no'}")
        lines.append("What is here: " + {"empty": "nothing yet (good for a new project)", "interview-in-progress": "an interview in progress",
                                         "project": "a project package", "partial-project": "part of a project package",
                                         "other-files": "other files"}.get(r.get("state", ""), "unknown"))
    lines.append(f"Helper checks can run: {'yes' if r['python_ok'] else 'no (done by hand instead)'} (Python {r['python']})")
    for p in r["problems"]:
        lines.append(f"PROBLEM: {p}")
    for n in r["notes"]:
        lines.append(f"Note: {n}")
    lines.append("Ready: " + ("yes" if r.get("ready") else "not yet"))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    r = check(Path(args[0]))
    print(json.dumps(r, indent=2) if "--json" in argv else as_text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
