# Start here — {{project_name}}

*{{one_liner}}*

This folder is your project's home. Everything Claude needs to keep building with you is written down in these plain text files, which you can open and read at any time. You never have to remember where you left off: the files remember.

## The files, in plain words

**For you:**

| File | What it is |
|---|---|
| `START-HERE.md` | This page. |
| `PROJECT_BRIEF.md` | What you told us about the project, as you confirmed it. The source of everything else. |

**Claude's working files** (you can open them any time, but you never need to; Claude reads them every session and tells you what matters):

| File | What it is |
|---|---|
| `CLAUDE.md` | The rules Claude follows every time it works on this project. |
| `PLAN.md` | The plan: small steps (we call them stories) to build one at a time, each with a ready-to-use instruction. |
| `BUILD_LOG.md` | The memory. After every working session, Claude adds what changed, how it was checked, and what to do next. |
<!-- if: size=standard,full -->
| `GUIDE-*.md` | Reference notes for this project: its words, and what it connects to or how it should look. |
<!-- /if -->
<!-- if: type=software; size=standard,full -->
| `FEATURE_MAP.md` | What is built so far, feature by feature: where each part lives and which steps changed it. It fills in as the project is built. |
<!-- /if -->
<!-- if: size=standard,full; safety=yes -->
| `SAFETY.md` | What must never happen, and who has to say yes before anything real is changed. |
<!-- /if -->

**Two signs you will see in the plan:** ★ means Claude will stop at that step and show you the result before going on. ⚠️ means that step needs extra care, because a quiet mistake there would be costly; it gets extra checks.

## How to use it

- **To begin or keep going**, tell Claude: *"What's next?"* It reads the files, tells you in one sentence what it is about to do, does it, checks it, and writes the log entry.
- **To pick up after a break**, open this same folder in a Cowork session (or Claude Code), then tell Claude: *"Where are we?"* It reads the files and tells you what is done, what is next and what is waiting on you. (A plain chat or the phone app can't see this folder.)
- **To add an idea later**, tell Claude: *"I want to add…"*. It asks a few questions, writes the new plan, and stops for you to look at it before building anything.
- **To stop and look at something**, say *"Let me review"*. Claude pauses and waits.
- **To change what the project is** (who it is for, what is in or out), say *"I want to change the brief"*. Claude goes through the change with you, and nothing is rebuilt without your yes.

## Who decides what

- **You ({{owner_name}})** own the plan and every decision in it. Claude suggests; you decide. You never have to edit these files yourself: when the plan needs to change, Claude explains the change and makes it once you say yes.
- **Claude** builds one story at a time, checks its own work, and tells you honestly what it checked and what it did not.
- Claude will stop and ask before anything that sends, publishes, deletes, spends money or changes real data, every time, even if you said yes before.

## How we agreed to work

- **Pauses:** {{review_cadence}}
- **Saving snapshots** (a saved copy of the project you can go back to): {{commit_policy}}

<!-- example: A filled version might read "Pauses: after every story that you will look at yourself, and always before anything is sent." and "Saving snapshots: only when I ask." -->

---

*Built with Project Method, by Wheelhouse.*
