#!/usr/bin/env python3
"""Check a generated project package. Standard library only; reads files and never changes anything.

Usage:  python3 -I check_package.py PROJECT_FOLDER [--before-log | --map-only]

--before-log  check everything except BUILD_LOG.md (generate-package runs this first, then writes the log with the real result,
              then runs the full check).
--map-only    check only FEATURE_MAP.md against the folder and the log (next-story runs this after updating the map).

Run by Claude after `generate-package` writes a package (and safe to run any time later). It reports ERRORS (the package is not
ready: fix before handing it to the owner) and WARNINGS (worth a look). Exit code 1 when there are errors.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

STORY_PARTS = ("**Reads first:**", "**Build:**", "**Tests:**", "**Done when:**", "**Prompt:**")
LOG_FIELDS = ("**Status:**", "**Files added:**", "**Files changed:**", "**What changed:**", "**Checked how:**",
              "**Deviations from the plan:**", "**Plan updates needed:**", "**Open questions / follow-ups:**")
TYPES = ("software", "data-analysis", "other")
SIZES = ("lite", "standard", "full")
LITE_MAX_STORIES = 8
MIN_STORIES = {"lite": 2, "standard": 4, "full": 4}
FULL_EXPECTED_STORIES = 8
MIN_PROMPT_WORDS = 12
MIN_FLAG_REASON_WORDS = 6
MAP_FIELDS = ("What it does:", "Where it lives:", "Depends on:", "Built and changed by:")
STEP_ID_RE = re.compile(r"\b(?:Story\s+)?(F?\d+\.\d+)\b")
STOPWORDS = {"about", "after", "their", "there", "which", "while", "would", "could", "should", "these", "those", "every", "other", "people", "where"}


def field_line(text: str, label: str) -> str | None:
    m = re.search(r"^\s*-\s*\*\*" + re.escape(label) + r"\*\*\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else None


def section(text: str, heading: str) -> str:
    m = re.search(r"^## " + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def expected_files(ptype: str, size: str, safety: bool) -> set[str]:
    files = {"START-HERE.md", "PROJECT_BRIEF.md", "CLAUDE.md", "PLAN.md", "BUILD_LOG.md"}
    if size in ("standard", "full"):
        files.add("GUIDE-glossary.md")
        files |= {"software": {"GUIDE-design.md", "GUIDE-reference.md", "FEATURE_MAP.md"}, "data-analysis": {"GUIDE-reference.md"},
                  "other": {"GUIDE-house-style.md"}}[ptype]
        if safety:
            files.add("SAFETY.md")
    return files


def parse_stories(plan: str) -> list[dict]:
    """Every '### Story <id> …' in the plan except the shape example ('Story X.X')."""
    stories = []
    for m in re.finditer(r"^### Story ([^\s—]+)(.*?)$(.*?)(?=^### |^## |\Z)", plan, re.M | re.S):
        sid, title, body = m.group(1), m.group(2), m.group(3)
        if sid.upper() == "X.X":
            continue
        stories.append({"id": sid, "title": title.strip(" —"), "body": body, "stop": "STOP FOR REVIEW" in title, "flag": "⚠️" in title or "⚠️" in body})
    return stories


def completed_steps(log: str) -> set[str]:
    """Story ids whose latest log entry says complete (a story may be logged partial first, then complete)."""
    latest: dict[str, str] = {}
    for m in re.finditer(r"^## \[\d{4}-\d{2}-\d{2}\] Story (F?\d+\.\d+)\b.*?$(.*?)(?=^## |\Z)", log, re.M | re.S):
        st = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", m.group(2))
        if st:
            latest[m.group(1)] = st.group(1).lower()
    return {sid for sid, status in latest.items() if status == "complete"}


def check_map(folder: Path, mapping: str, log: str) -> list[tuple[str, str, str]]:
    """FEATURE_MAP.md: every entry has its four lines, every path it names exists, every finished step is listed."""
    errors: list[tuple[str, str, str]] = []
    if "## Features" not in mapping:
        return [("PK-MAP", "FEATURE_MAP.md", "missing the '## Features' section")]
    if "## Steps that changed no feature" not in mapping:
        errors.append(("PK-MAP", "FEATURE_MAP.md", "missing the '## Steps that changed no feature' section"))
    features = section(mapping, "Features")
    listed: set[str] = set()
    for m in re.finditer(r"^### (.+?)\s*$(.*?)(?=^### |\Z)", features, re.M | re.S):
        name, body = m.group(1).strip(), m.group(2)
        where = f"FEATURE_MAP.md: {name}"
        for label in MAP_FIELDS:
            if field_line(body, label) is None:
                errors.append(("PK-MAP", where, f"missing the **{label}** line"))
        for path in re.findall(r"`([^`]+)`", field_line(body, "Where it lives:") or ""):
            if not (folder / path.strip().rstrip("/")).exists():
                errors.append(("PK-MAP-PATH", where, f"lists `{path}`, which is not in the project folder"))
        listed |= set(STEP_ID_RE.findall(field_line(body, "Built and changed by:") or ""))
    listed |= set(STEP_ID_RE.findall(section(mapping, "Steps that changed no feature")))
    for sid in sorted(completed_steps(log) - listed):
        errors.append(("PK-MAP-STEP", "FEATURE_MAP.md", f"Story {sid} is complete in the log but not in the map (add it to a feature, or under 'Steps that changed no feature')"))
    return errors


def check(folder: Path, before_log: bool = False) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    folder = Path(folder)
    errors: list[tuple[str, str, str]] = []
    warnings: list[tuple[str, str, str]] = []
    err = lambda code, where, msg: errors.append((code, where, msg))  # noqa: E731
    warn = lambda code, where, msg: warnings.append((code, where, msg))  # noqa: E731

    brief_path = folder / "PROJECT_BRIEF.md"
    if not brief_path.is_file():
        err("PK-BRIEF", "PROJECT_BRIEF.md", "missing: the package is generated from a confirmed brief")
        return errors, warnings
    brief = brief_path.read_text(encoding="utf-8")
    if "Interview progress" in brief or not re.search(r"^Confirmed by .+ on \d{4}-\d{2}-\d{2}", brief, re.M):
        err("PK-BRIEF", "PROJECT_BRIEF.md", "the brief is not confirmed (no 'Confirmed by <owner> on <date>' line, or the interview is still in progress)")
    if "Not answered yet" in brief:
        err("PK-BRIEF", "PROJECT_BRIEF.md", "has fields marked 'Not answered yet'")
    def first_word(label: str) -> tuple[str, str]:
        raw = (field_line(brief, label) or "").strip()
        m = re.match(r"[A-Za-z-]+", raw)
        return (m.group(0).lower() if m else ""), raw

    ptype, raw_type = first_word("Type of project:")
    size, raw_size = first_word("Size of the plan:")
    m = re.search(r"\*\*Can it change anything real\*\*[^?]*\?\s*(.*)$", brief, re.M)
    real = m.group(1).strip() if m else ""
    safety = real.lower().startswith("yes")
    if ptype not in TYPES:
        err("PK-BRIEF", "PROJECT_BRIEF.md", f"type of project is {raw_type!r}; it must start with one of {', '.join(TYPES)}")
        ptype = ""
    elif raw_type.lower() != ptype:
        warn("PK-BRIEF", "PROJECT_BRIEF.md", "write the type of project as just the word; any explanation belongs elsewhere")
    if size not in SIZES:
        err("PK-BRIEF", "PROJECT_BRIEF.md", f"size of the plan is {raw_size!r}; it must start with one of {', '.join(SIZES)}")
        size = ""
    elif raw_size.lower() != size:
        warn("PK-BRIEF", "PROJECT_BRIEF.md", "write the size of the plan as just the word; the reason goes under 'Why this size'")
    if field_line(brief, "Owner (makes the decisions):") is None:
        warn("PK-BRIEF", "PROJECT_BRIEF.md", "no 'Owner (makes the decisions):' line")
    deadline = field_line(brief, "Deadline:")
    if deadline and deadline.rstrip(".").lower() != "none" and not re.match(r"\d{4}-\d{2}-\d{2}$", deadline.rstrip(".")):
        warn("PK-BRIEF", "PROJECT_BRIEF.md", f"the deadline {deadline!r} should be an exact date (YYYY-MM-DD) or 'None'")
    if safety and size == "lite":
        err("PK-SAFETY", "PROJECT_BRIEF.md", "the project can change something real, so the plan must be Standard or Full, not Lite")

    present = {p.name for p in folder.glob("*.md")}
    want = expected_files(ptype, size, safety) if ptype and size else {"START-HERE.md", "PROJECT_BRIEF.md", "CLAUDE.md", "PLAN.md", "BUILD_LOG.md"}
    for name in sorted(want - present):
        if before_log and name == "BUILD_LOG.md":
            continue
        err("PK-FILES", name, "missing for this type and size")
    texts = {name: (folder / name).read_text(encoding="utf-8") for name in present}
    for name, text in sorted(texts.items()):
        if "{{" in text or "}}" in text:
            err("PK-PLACEHOLDER", name, "a {{placeholder}} was left unfilled")
        if "<!--" in text or "-->" in text:
            err("PK-MARKER", name, "a template comment or marker was left in")

    plan = texts.get("PLAN.md", "")
    stories = parse_stories(plan) + parse_stories(texts.get("FEATURE_PLAN.md", ""))
    ids = [s["id"] for s in stories]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        err("PK-STORY-ID", "PLAN.md", f"story {dup} appears more than once")
    made_by_earlier: set[str] = set()
    for s in stories:
        where = f"PLAN.md: Story {s['id']}"
        for part in STORY_PARTS:
            if part not in s["body"]:
                err("PK-STORY", where, f"missing {part}")
        pm = re.search(r"\*\*Prompt:\*\*\s*```(.*?)```", s["body"], re.S)
        if "**Prompt:**" in s["body"] and (not pm or len(pm.group(1).split()) < MIN_PROMPT_WORDS):
            err("PK-PROMPT", where, f"the prompt must be a ready-to-paste block of at least {MIN_PROMPT_WORDS} words")
        if s["flag"]:
            fm = re.search(r"⚠️\s*\*\*(?:Complex|Needs extra care)[^*]*\*\*(.*)$", s["body"], re.M)
            # the banner's own "(a stronger model … helps here):" is not the reason; drop it before counting
            reason = re.sub(r"^\s*\([^)]*\)\s*:?\s*", "", fm.group(1)) if fm else ""
            if fm and len(reason.split()) < MIN_FLAG_REASON_WORDS:  # the reason may also sit on the next line
                after = s["body"][fm.end():].lstrip("\n").split("\n", 1)[0]
                reason = reason + " " + after.lstrip("> ").strip()
            if not fm or len(reason.split()) < MIN_FLAG_REASON_WORDS or reason.strip().startswith("**"):
                err("PK-FLAG", where, "a ⚠️ story must say in a sentence why a mistake would be costly")
        reads = re.search(r"\*\*Reads first:\*\*(.*?)\n", s["body"])
        for ref in sorted(set(re.findall(r"(?<![\w/.-])([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.md)\b", reads.group(1) if reads else ""))):
            if ref not in present and ref != "FEATURE_PLAN.md" and ref not in made_by_earlier:
                err("PK-READS", where, f"reads {ref}, which is not in this package and no earlier story says it makes it")
        build = re.search(r"\*\*Build:\*\*(.*?)(?=\n\*\*[A-Z][^*]*:\*\*|\Z)", s["body"], re.S)
        made_by_earlier |= set(re.findall(r"([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.md)\b", build.group(1) if build else ""))
    n = len(parse_stories(plan))
    if size and size == "lite" and n > LITE_MAX_STORIES:
        err("PK-SIZE", "PLAN.md", f"a Lite plan has at most {LITE_MAX_STORIES} stories; this one has {n}. Make it Standard, or trim it.")
    if size and n < MIN_STORIES[size]:
        err("PK-SIZE", "PLAN.md", f"a {size} plan needs at least {MIN_STORIES[size]} stories; this one has {n}")
    if size == "full" and n < FULL_EXPECTED_STORIES:
        warn("PK-SIZE", "PLAN.md", f"a Full plan usually has {FULL_EXPECTED_STORIES} or more stories; this one has {n}")
    plan_ids = [st["id"] for st in parse_stories(plan)]
    if "0.1" not in plan_ids or "0.2" not in plan_ids:
        err("PK-STORY", "PLAN.md", "the first two stories (set-up/definitions/outline, then the open questions) must be kept")
    if not any(s["stop"] for s in stories):
        err("PK-STOP", "PLAN.md", "no story ends at a review gate (★ STOP FOR REVIEW); the owner must get at least one look before the end")
    if safety:
        if not any(s["flag"] for s in stories):
            err("PK-SAFETY", "PLAN.md", "the project can change something real but no story is flagged ⚠️ (needs extra care)")
        reads_safety = any("SAFETY.md" in (re.search(r"\*\*Reads first:\*\*(.*?)\n", st["body"]) or [None, ""])[1] for st in stories)
        if "SAFETY.md" in present and not reads_safety:
            err("PK-SAFETY", "PLAN.md", "no story lists SAFETY.md under 'Reads first'")

    # every open question from the brief reaches the plan
    for item in re.findall(r"^- (.+)$", section(brief, "Open questions"), re.M):
        if item.strip() not in plan:
            err("PK-OPEN", "PLAN.md", f"open question not carried into the plan: {item.strip()!r}")
    # every in-scope item shows up in at least one story beyond the first two
    scope = field_line(brief, "In scope (we are doing this):") or ""
    later_stories = [(s["title"] + s["body"]).lower() for s in stories if not s["id"].startswith("0.")]
    items = [i.strip() for i in scope.split(";") if i.strip()]

    def distinctive(word: str) -> bool:
        """A word that is in every story (or nearly) says nothing about whether this item has one."""
        hits = sum(1 for t in later_stories if word in t)
        return bool(later_stories) and hits <= max(1, int(len(later_stories) * 0.6))
    if not items:
        warn("PK-SCOPE", "PROJECT_BRIEF.md", "the in-scope line is empty or not on one line; write the items on that line separated by semicolons")
    for item in items:
        # compare stems, so "emailing" finds "email" and "previewing" finds "preview"
        words = sorted({w[:5] if len(w) >= 7 else w for w in re.findall(r"[a-z]{5,}", item.lower()) if w not in STOPWORDS})
        telling = [w for w in words if distinctive(w)]
        if not words or (not telling and all(any(w in t for t in later_stories) for w in words)):
            continue  # nothing distinctive to look for: cannot tell either way
        if not any(w in t for w in telling for t in later_stories):
            warn("PK-SCOPE", "PLAN.md", f"no story seems to build the in-scope item {item!r}")

    log = "" if before_log else texts.get("BUILD_LOG.md", "")
    if log:
        if "## Entry format" not in log:
            err("PK-LOG", "BUILD_LOG.md", "missing the entry format")
        for f in LOG_FIELDS:
            if f not in log:
                err("PK-LOG", "BUILD_LOG.md", f"the entry format is missing {f}")
        if not re.search(r"^## \[\d{4}-\d{2}-\d{2}\] ", log, re.M):
            err("PK-LOG", "BUILD_LOG.md", "no dated first entry")
    rules = texts.get("CLAUDE.md", "")
    if rules:
        for needle in ("House rules", "Before finishing any story", "STOP FOR REVIEW"):
            if needle not in rules:
                err("PK-RULES", "CLAUDE.md", f"missing {needle!r}")
        if not section(rules, "What must never happen").strip():
            err("PK-RULES", "CLAUDE.md", "'What must never happen' is empty")
    if "FEATURE_MAP.md" in texts:
        errors.extend(check_map(folder, texts["FEATURE_MAP.md"], log))
    if "START-HERE.md" in texts and "What's next?" not in texts["START-HERE.md"]:
        err("PK-START", "START-HERE.md", "does not tell the owner how to continue ('What's next?')")
    return errors, warnings


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    folder = Path(args[0])
    if "--map-only" in argv:
        mp, lg = folder / "FEATURE_MAP.md", folder / "BUILD_LOG.md"
        if not mp.is_file():
            print(f"There is no FEATURE_MAP.md in {folder}; nothing to check.")
            return 0
        errors, warnings = check_map(folder, mp.read_text(encoding="utf-8"), lg.read_text(encoding="utf-8") if lg.is_file() else ""), []
    else:
        errors, warnings = check(folder, before_log="--before-log" in argv)
    for code, where, msg in errors:
        print(f"ERROR   {code:15} {where}: {msg}")
    for code, where, msg in warnings:
        print(f"warning {code:15} {where}: {msg}")
    note = " (log not checked yet)" if "--before-log" in argv else " (feature map only)" if "--map-only" in argv else ""
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s) in {args[0]}" + note)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
