#!/usr/bin/env python3
"""Work out the next story to build and the pauses it needs. Standard library only; reads files and never changes anything.

Usage:  python3 -I next_story.py PROJECT_FOLDER [--json]

Used by the `next-story` skill at the start of every story. It reads PLAN.md (and FEATURE_PLAN.md for approved features),
BUILD_LOG.md and PROJECT_BRIEF.md, and reports: which story is next and why, what to read first, every pause the story needs, the
words in it that may mean an action that cannot be undone (to watch for), and any plan change the owner still has to make.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Words that ARE an action wherever they appear. Nouns that are also verbs ("text", "email", "message", "post") are matched
# separately, only when used as an action (see AS_ACTION), so "which text service" does not raise a false alarm.
OUTWARD_WORDS = ("send", "sends", "sending", "emailing", "texting", "sms", "notify", "notifies", "publish", "publishes", "publishing", "post", "posting",
                 "delete", "deletes", "deleting", "remove", "pay", "pays", "payment", "payments", "charge", "purchase", "submit",
                 "upload", "share", "invite", "go live", "release", "update the real", "change the real", "real send", "first real")
ALWAYS_READ = ("CLAUDE.md", "the last three to five entries of BUILD_LOG.md")
AS_ACTION = re.compile(r"(?:^|[-*•]\s*|\bto\s+|\bwill\s+|\bthen\s+)(text|texts|email|emails|message|messages|post|posts)\s+(?:the|a|an|each|every|all|them|him|her|it|to|out|everyone|\w+'s)\b", re.I | re.M)


def parse_stories(text: str, source: str) -> list[dict]:
    out = []
    for m in re.finditer(r"^### Story ([^\s—]+)(.*?)$(.*?)(?=^### |^## |\Z)", text, re.M | re.S):
        sid, title, body = m.group(1), m.group(2), m.group(3)
        if sid.upper() == "X.X":
            continue
        reads = re.search(r"\*\*Reads first:\*\*(.*?)\n", body)
        out.append({
            "id": sid, "title": title.strip(" —").replace("★ STOP FOR REVIEW", "").replace("⚠️", "").strip(" —"),
            "source": source, "body": body, "stop": "STOP FOR REVIEW" in title, "flag": "⚠️" in title or "⚠️" in body,
            "reads": reads.group(1).strip() if reads else "",
        })
    return out


def approved_features(feature_plan: str) -> set[str]:
    """Feature numbers whose row in the FEATURE_PLAN index says Approved (or Building)."""
    ok = set()
    for m in re.finditer(r"^\|\s*(\d+)\s*\|[^|]*\|[^|]*\|\s*([^|]*)\|", feature_plan, re.M):
        if re.search(r"\b(approved|building)\b", m.group(2), re.I):
            ok.add(m.group(1))
    return ok


ENTRY_RE = re.compile(r"^## \[?(\d{4}-\d{2}-\d{2})\]?\s+(.*?)$(.*?)(?=^## \[?\d{4}-\d{2}-\d{2}|\Z)", re.M | re.S)
STORY_ID_RE = re.compile(r"Story\s+([A-Za-z]?\d+(?:\.\d+)?)")


def log_entries(log: str) -> list[dict]:
    """Every dated entry, tolerant of hand edits: brackets optional, any dash, any capitalisation of the status."""
    out = []
    for m in ENTRY_RE.finditer(log):
        date, head, body = m.group(1), m.group(2).strip(), m.group(3)
        sm = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", body)
        um = re.search(r"\*\*Plan updates needed:\*\*\s*(.*)", body)
        idm = STORY_ID_RE.match(head)
        out.append({"date": date, "head": head, "story": idm.group(1) if idm else None,
                    "status": sm.group(1).lower() if sm else None, "plan_updates": um.group(1).strip() if um else ""})
    return out


def is_none(text: str) -> bool:
    return text.strip().lower().rstrip(".") in ("", "none", "none yet", "n/a")


def pending_plan_updates(log: str) -> list[str]:
    """Plan changes asked for in the log and not yet made: every non-empty 'Plan updates needed' since the last
    'Plan updated' entry (Claude adds that entry when it makes the changes, with the owner's yes)."""
    pending: list[str] = []
    for e in log_entries(log):
        if re.match(r"plan updated\b", e["head"], re.I):
            pending = []
            continue
        if not is_none(e["plan_updates"]):
            pending.append(e["plan_updates"])
    return pending


def log_status(log: str) -> tuple[dict[str, str], str]:
    """The latest status recorded for each story, and the plan changes still waiting (joined)."""
    status: dict[str, str] = {}
    for e in log_entries(log):
        if e["story"] and e["status"]:
            status[e["story"]] = e["status"]
    return status, " | ".join(pending_plan_updates(log))


def mentions(story_id: str, text: str) -> bool:
    """Whether text names this exact story ('1.1' must not match '1.12' or 'F1.1')."""
    return bool(re.search(r"(?<![\w.])" + re.escape(story_id) + r"(?![\d])", text))


def brief_line(brief: str, label: str) -> str:
    m = re.search(r"^\s*-\s*\*\*" + re.escape(label) + r"\*\*\s*(.*)$", brief, re.M)
    return m.group(1).strip() if m else ""


def outward_hits(story: dict) -> list[str]:
    """Words in the title, Build and Done-when that may mean an action that cannot be undone."""
    parts = [story["title"]]
    for label in ("**Build:**", "**Done when:**"):
        m = re.search(re.escape(label) + r"(.*?)(?=\n\*\*[A-Z][^*]*:\*\*|\Z)", story["body"], re.S)
        if m:
            parts.append(m.group(1))
    text = " ".join(parts)
    hits = {w for w in OUTWARD_WORDS if re.search(r"\b" + re.escape(w) + r"\b", text.lower())}
    hits |= {m.group(1).lower() for m in AS_ACTION.finditer(text)}
    return sorted(hits)


def analyse(folder: Path) -> dict:
    folder = Path(folder)
    read = lambda n: (folder / n).read_text(encoding="utf-8") if (folder / n).is_file() else ""  # noqa: E731
    plan, feature_plan, log, brief = read("PLAN.md"), read("FEATURE_PLAN.md"), read("BUILD_LOG.md"), read("PROJECT_BRIEF.md")
    if not plan or not log:
        return {"state": "no-package", "message": "There is no PLAN.md and BUILD_LOG.md here. Start with the start skill, or open the project's folder."}
    stories = parse_stories(plan, "PLAN.md")
    ok_features = approved_features(feature_plan)
    stories += [s for s in parse_stories(feature_plan, "FEATURE_PLAN.md") if re.match(r"F(\d+)\.", s["id"]) and re.match(r"F(\d+)\.", s["id"]).group(1) in ok_features]
    status, updates = log_status(log)
    pending = [s for s in stories if status.get(s["id"]) != "complete"]
    if not pending:
        return {"state": "all-done", "message": "Every story in the plan (and every approved feature) is recorded as complete. Offer where-are-we for a summary, or add-feature for a new idea."}
    nxt = pending[0]
    was = status.get(nxt["id"])
    why = (f"the log records Story {nxt['id']} as {was}, so it is resumed before anything else" if was in ("partial", "blocked")
           else "it is the first story in the plan that the log does not record as complete")
    reads_safety = "SAFETY.md" in nxt["reads"]
    # the first real action that cannot be undone: the first story (in order) that ends at a review gate, needs extra care,
    # reads SAFETY.md and names an outward action; or any story that says it is the first real one
    first_real_id = next((st["id"] for st in stories if st["stop"] and st["flag"] and "SAFETY.md" in st["reads"] and outward_hits(st)), None)
    commits = brief_line(brief, "Saving snapshots (commits):").lower()
    cadence = brief_line(brief, "Pauses:").lower()
    auto_commit = bool(re.search(r"after (each|every) (story|step)|automatic", commits))
    every_step = bool(re.search(r"after (each|every) (story|step)", cadence))
    pauses = [{"when": "before starting", "kind": "announce", "what": "Tell the owner in one sentence which story you are starting and what it will produce."}]
    if was == "blocked":
        pauses.append({"when": "before starting", "kind": "blocked", "what": "The last session was blocked on this story. Read why in the log and check with the owner that the blocker is cleared before building."})
    if re.search(r"wait for the owner to (choose|decide|pick)|wait for (?:the owner'?s? )?(?:choice|decision)", nxt["body"], re.I):
        pauses.append({"when": "before building", "kind": "decision", "what": "This story asks the owner to choose before anything is built. Present the choice in plain words, wait for the answer, then build what they chose."})
    if nxt["flag"]:
        pauses.append({"when": "before building", "kind": "confirm-approach", "what": "This story is marked ⚠️ (needs extra care). Say in plain words how you will do it and how you will check it, and wait for the owner's yes."})
    deps = [d for d in re.findall(r"Story (\d+\.\d+|F\d+\.\d+)", nxt["reads"]) if status.get(d) != "complete"]
    if deps:
        pauses.append({"when": "before starting", "kind": "dependency", "what": f"This story reads the work of Story {', '.join(sorted(set(deps)))}, which the log does not record as complete. Tell the owner and do that first."})
    if updates and mentions(nxt["id"], updates):
        pauses.append({"when": "before starting", "kind": "plan-update", "what": "The latest log entry asks the owner to change the plan for this story. Check with the owner that the change has been made (or that they want to go ahead without it)."})
    if reads_safety:
        pauses.append({"when": "during", "kind": "safety", "what": "Follow SAFETY.md. Try every real change on the test copy first, through the single checked doorway."})
    first_real = nxt["id"] == first_real_id or (nxt["flag"] and reads_safety and bool(re.search(r"first real", nxt["title"] + nxt["body"], re.I)))
    if first_real:
        pauses.append({"when": "before the action", "kind": "try-once-first", "what": "This is the first real action that cannot be undone. Do it for ONE real target only. Show the owner exactly what will happen (target, address or place, content, amount) and wait for a fresh yes. Then check it worked before anything more."})
    hits = outward_hits(nxt)
    if hits:
        pauses.append({"when": "before the action", "kind": "outward", "what": "If this story actually sends, publishes, deletes, pays or changes real data (the words below suggest it might): before that action, use the checklist in references/before-outward-actions.md and get a fresh yes for that exact action, even if the owner said yes before."})
    log_pause = {"when": "before finishing", "kind": "log", "what": "Run the story's checks (for each new check, break it on purpose first and put it back), use the result as a real person would, then write the log entry honestly in the exact format."}
    commit_pause = {"when": "before finishing", "kind": "commit", "what": "Save a snapshot (commit) now, and say so." if auto_commit else "Do not save a snapshot (commit) unless the owner asks; offer it in one line, asking for an exact reply ('say \"save a snapshot\" if you want one')."}
    checks_pause = {"when": "before finishing", "kind": "checks", "what": "Run the story's checks (for each new check, break it on purpose first and put it back) and use the result as a real person would."}
    log_after = {"when": "after the owner answers", "kind": "log", "what": "Write the log entry after the owner answers: complete if they approved; partial (and why) if they asked for changes not yet made or stopped before answering."}
    if nxt["stop"]:
        pauses.append(checks_pause)
        pauses.append({"when": "at the end", "kind": "review-gate", "what": "This story ends at a review gate (★). Use review-gate: what exists, how to look at it, what was checked, decisions needed with a recommendation each. Then wait."})
        pauses.append(log_after)
        pauses.append(dict(commit_pause, when="after the owner answers"))
    elif every_step:
        pauses.append(checks_pause)
        pauses.append({"when": "at the end", "kind": "review", "what": "The owner asked to see every step: show what changed and how to look at it, and wait before starting the next story."})
        pauses.append(log_after)
        pauses.append(dict(commit_pause, when="after the owner answers"))
    else:
        pauses.append(log_pause)
        pauses.append(commit_pause)
        pauses.append({"when": "at the end", "kind": "report", "what": "Report in plain words what changed and what to look at. Continue only if the owner says so."})
    reads = nxt["reads"] or "(the story names nothing else)"
    read_first = [*ALWAYS_READ, reads] if "CLAUDE.md" not in reads else [ALWAYS_READ[1], reads]
    return {
        "state": "next", "story": nxt["id"], "title": nxt["title"], "source": nxt["source"], "why": why,
        "read_first": read_first,
        "pauses": pauses, "watch_for": hits, "plan_updates_waiting": updates,
        "remaining": len(pending),
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    r = analyse(Path(args[0]))
    if "--json" in argv:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    if r["state"] != "next":
        print(r["message"])
        return 0
    print(f"Next story: {r['story']} — {r['title']}  ({r['source']}; {r['remaining']} not yet complete)")
    print(f"Why: {r['why']}.")
    print("Read first: " + "; ".join(r["read_first"]))
    print("Pauses this story needs:")
    for p in r["pauses"]:
        print(f"  - [{p['when']}] {p['what']}")
    if r["watch_for"]:
        print("Watch for actions that cannot be undone (words found in the story): " + ", ".join(r["watch_for"]))
    if r["plan_updates_waiting"]:
        print("Plan change the owner was asked to make (latest log entry): " + r["plan_updates_waiting"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
