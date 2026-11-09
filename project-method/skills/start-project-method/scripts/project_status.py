#!/usr/bin/env python3
"""Where does the project stand? Standard library only; reads files and never changes anything.

Usage:  python3 -I project_status.py PROJECT_FOLDER [--json]

Used by the `where-are-we` skill. Copes with files edited by hand and with missing files (it says what it could not read
instead of guessing). Uses next_story.py, from the same folder, for "what's next", so the status and the build runner agree.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("next_story", Path(__file__).with_name("next_story.py"))
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)  # type: ignore[union-attr]

CORE = ("PROJECT_BRIEF.md", "CLAUDE.md", "PLAN.md", "BUILD_LOG.md")


def brief_line(brief: str, label: str) -> str:
    m = re.search(r"^\s*-\s*\*\*" + re.escape(label) + r"\*\*\s*(.*)$", brief, re.M)
    return m.group(1).strip() if m else ""


def status(folder: Path, today: str | None = None) -> dict:
    folder = Path(folder)
    read = lambda n: (folder / n).read_text(encoding="utf-8") if (folder / n).is_file() else None  # noqa: E731
    files = {n: read(n) for n in (*CORE, "FEATURE_PLAN.md", "START-HERE.md")}
    missing = [n for n in CORE if files[n] is None]
    brief, plan, log, fplan = (files[n] or "" for n in ("PROJECT_BRIEF.md", "PLAN.md", "BUILD_LOG.md", "FEATURE_PLAN.md"))
    out: dict = {"missing": missing, "unreadable_entries": [], "waiting_on_owner": [], "notes": []}

    name = re.search(r"^# Project Brief — (.+)$", brief, re.M)
    out["project"] = name.group(1).strip() if name else (folder.name if not brief else "this project")
    out["type"] = brief_line(brief, "Type of project:") or "unknown"
    out["size"] = brief_line(brief, "Size of the plan:") or "unknown"
    for k in ("type", "size"):
        if "not answered" in out[k].lower():
            out[k] = f"{k} not decided yet"
    out["owner"] = (re.search(r"^Confirmed by (.+?) on \d{4}-\d{2}-\d{2}", brief, re.M) or [None, ""])[1]
    if brief and "Interview progress" in brief:
        out["stage"] = "interview"
        out["missing"] = []  # nothing is missing yet: the package comes after the interview
        out["notes"].append(re.search(r"Interview progress[^\n]*", brief).group(0).strip("> *"))
        out["say_next"] = "Say you want to continue your project, and the interview picks up where it stopped."
        return out
    if "PROJECT_BRIEF.md" in missing and "PLAN.md" in missing:
        out["stage"] = "nothing-here"
        out["say_next"] = "This folder has no project yet. Say what you would like to build to start one."
        return out
    if "PLAN.md" in missing or "BUILD_LOG.md" in missing:
        out["stage"] = "incomplete-package"
        out["say_next"] = "Some package files are missing. Ask to rebuild the package from the brief (generate-package); the log is never overwritten."
        return out

    plan_stories = N.parse_stories(plan, "PLAN.md")
    feat_stories = N.parse_stories(fplan, "FEATURE_PLAN.md")
    entries = N.log_entries(log)
    st, updates = N.log_status(log)
    out["unreadable_entries"] = [e["head"] for e in entries if e["story"] and not e["status"]]
    out["owner_notes"] = [f"{e['date']}: {e['head']}" for e in entries if not e["story"] and not e["status"]]
    import datetime as _dt
    _today = today or _dt.date.today().isoformat()
    dates = [e["date"] for e in entries]
    future = sorted({d for d in dates if d > _today})
    backwards = [b for a, b in zip(dates, dates[1:]) if b < a]
    if future:
        out["notes"].append(f"Some log entries are dated in the future ({', '.join(future)}); check the dates are right.")
    if backwards:
        out["notes"].append("Some log entries are out of date order; the log is read top to bottom, so check which came last.")
    done = [s["id"] for s in plan_stories if st.get(s["id"]) == "complete"]
    out["plan"] = {"done": len(done), "total": len(plan_stories), "partial_or_blocked": [s["id"] for s in plan_stories if st.get(s["id"]) in ("partial", "blocked")]}
    feats = []
    for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|", fplan, re.M):
        feats.append({"n": m.group(1), "name": m.group(2), "status": m.group(4)})
    out["features"] = feats
    for f in feats:
        if re.search(r"draft|waiting", f["status"], re.I):
            out["waiting_on_owner"].append(f"Feature {f['n']} ({f['name']}) is written and waiting for your review before anything is built.")
    sessions = [e for e in entries if e["status"]]
    last = sessions[-1] if sessions else None
    out["last_session"] = {"date": last["date"], "what": last["head"], "status": last["status"]} if last else None
    if last and last["story"]:
        story = next((s for s in plan_stories + feat_stories if s["id"] == last["story"]), None)
        if story and story["stop"] and last["status"] == "partial":
            out["waiting_on_owner"].append(f"Story {last['story']} stopped at a review gate; your answers to its questions are needed before the next story.")
        elif last["status"] in ("partial", "blocked"):
            out["waiting_on_owner"].append(f"The last session ({last['date']}) left Story {last['story']} {last['status']}; read its log entry for why.")
    for u in N.pending_plan_updates(log):
        out["waiting_on_owner"].append(f"A plan change was asked for and not yet made: {u}")
    if "0.2" in [s["id"] for s in plan_stories] and st.get("0.2") != "complete":
        opens = re.findall(r"^- (.+)$", re.search(r"## Open questions\s*$(.*?)(?=^## |\Z)", brief, re.M | re.S).group(1), re.M) if "## Open questions" in brief else []
        if opens:
            out["open_questions"] = len(opens)
    deadline = brief_line(brief, "Deadline:").rstrip(".")
    out["deadline"] = deadline if re.match(r"\d{4}-\d{2}-\d{2}$", deadline) else None
    if out["deadline"]:
        import datetime
        now = today or datetime.date.today().isoformat()
        left = out["plan"]["total"] - out["plan"]["done"]
        if now > out["deadline"] and left:
            out["waiting_on_owner"].append(f"The deadline ({out['deadline']}) has passed with {left} stor{'y' if left == 1 else 'ies'} left; decide whether to move the date or trim the plan.")
    nxt = N.analyse(folder)
    out["next"] = {"story": nxt.get("story"), "title": nxt.get("title"), "source": nxt.get("source")} if nxt["state"] == "next" else None
    out["stage"] = "building" if nxt["state"] == "next" else "all-done"
    if out["unreadable_entries"]:
        out["notes"].append(f"{len(out['unreadable_entries'])} log entr{'y has' if len(out['unreadable_entries']) == 1 else 'ies have'} no readable status; they were not counted.")
    if out.get("open_questions"):
        msg = f"{out['open_questions']} open question(s) from the brief still need answers"
        if out.get("next") and out["next"]["story"] == "0.2":
            out["notes"].append(msg + "; Story 0.2, which is next, works through them with you.")
        else:
            out["waiting_on_owner"].append(msg + " (Story 0.2).")
    if out["waiting_on_owner"]:
        out["say_next"] = "Answer what is waiting on you first; then say \"What's next?\"."
    elif out["stage"] == "all-done":
        out["say_next"] = "Everything planned is done. Say \"I want to add…\" for a new idea."
    else:
        out["say_next"] = f"Say \"What's next?\" to start Story {out['next']['story']}."
    return out


def as_text(s: dict) -> str:
    lines = [f"Project: {s['project']}" + (f" ({s['type']}, {s['size']})" if s.get("type") != "unknown" else "") + (f", owner {s['owner']}" if s.get("owner") else "")]
    if s.get("missing"):
        lines.append("Missing files: " + ", ".join(s["missing"]))
    if s["stage"] in ("building", "all-done"):
        p = s["plan"]
        lines.append(f"Plan: {p['done']} of {p['total']} stories done" + (f"; in progress or stuck: {', '.join(p['partial_or_blocked'])}" if p["partial_or_blocked"] else "") + ".")
        if s["features"]:
            lines.append("Features: " + "; ".join(f"{f['n']}. {f['name']} — {f['status']}" for f in s["features"]))
        if s.get("last_session"):
            ls = s["last_session"]
            lines.append(f"Last session: {ls['date']}, {ls['what']}" + (f" ({ls['status']})" if ls["status"] else ""))
        if s.get("next"):
            lines.append(f"Next: Story {s['next']['story']} — {s['next']['title']}")
    if s.get("deadline"):
        lines.append(f"Deadline: {s['deadline']}")
    if s.get("owner_notes"):
        lines.append("Notes added to the log: " + "; ".join(s["owner_notes"]))
    if s["waiting_on_owner"]:
        lines.append("Waiting on you:")
        lines += [f"  - {w}" for w in s["waiting_on_owner"]]
    for n in s["notes"]:
        lines.append(f"Note: {n}")
    lines.append(f"What to say next: {s['say_next']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    s = status(Path(args[0]))
    print(json.dumps(s, indent=2, ensure_ascii=False) if "--json" in argv else as_text(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
