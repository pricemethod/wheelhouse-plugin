# How to write a log entry

The log is the memory between sessions. The exact format is in `templates/parts/log-format.md` and is the same in the rules file and the log itself. This page says how to write one that the next session can trust.

## Rules

- **Append only.** Never edit or delete an earlier entry. A mistake in an old entry is corrected by a new entry that says so.
- **The log wins.** If the log and the plan disagree, the log is right, and the entry says it is overriding the plan.
- **Write it before saying the story is done**, and only after the work was actually checked. For a story that ends at a review gate, write it after the owner answers.
- **Say what really happened.** A check that failed, a check that was skipped and a check that could not be run are each named. "Not tested" is a perfectly good thing to write; "tested" when it was not is the one unforgivable entry.
- **Keep it short, link to the work.** Name the files; do not paste them.
- **"Plan updates needed" is a proposal.** Name the exact story and the exact change, and explain it to the owner. Make it only after they say yes to it, then add a "Plan updated" entry. A change stays waiting until that entry exists.
- **Entries that are not a story** use the same fields under one of these headings: "Plan updated — …", "Brief changed — …", "Feature <n> added — …", "Package regenerated — …", or "Note — …" (a note has no status).

## What each field is for

| Field | What the next session needs from it |
|---|---|
| Status | complete, partial or blocked: can I build on this? |
| Files added / changed | where to look |
| What changed | one to three plain sentences |
| Checked how | what was run or looked at, and with what data or setup, so the check can be repeated |
| Deviations | where reality differed from the plan, and why |
| Plan updates needed | what the owner has to change before the next story |
| Open questions / follow-ups | what would surprise the next session |

## Example: a good entry (invented project)

```
## [2026-03-12] Story 2.1 — Send the request email
**Status:** complete
**Files added:** mail/send_request.py, tests/test_send_request.py
**Files changed:** SAFETY.md (added the test-inbox name)
**What changed:** a request now sends one email to the tool's owner, once per request, through the single send doorway; only the test inbox is allowed for now.
**Checked how:** ran the checks (all pass); sent two requests for the same tool and saw one email in the test inbox; broke the doorway check on purpose, saw it fail, restored it. Nothing was sent to a real address.
**Deviations from the plan:** none.
**Plan updates needed:** none.
**Open questions / follow-ups:** the owner has not yet read the email wording; do that before any real neighbor is emailed.
```

## Example: an honest partial entry

```
## [2026-03-14] Story 2.2 — Reminder when a tool is due back
**Status:** partial
**Files added:** reminders/due_soon.py
**Files changed:** none
**What changed:** the list of tools due back tomorrow is built; the email itself is not written.
**Checked how:** the list matches a hand count for the sample week. The sending part was not built, so it was not checked.
**Deviations from the plan:** stopped before the email because the owner has not decided the wording (see below).
**Plan updates needed:** Story 2.2: split into "build the list" (done) and "send the reminder" (waiting on wording).
**Open questions / follow-ups:** the owner needs to choose between a friendly and a formal reminder.
```
