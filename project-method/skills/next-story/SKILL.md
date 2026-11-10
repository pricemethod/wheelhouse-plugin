---
name: next-story
description: "Runs the build one story at a time for a project that already has a package. Use when the user says 'what's next', 'go', 'continue', 'build the next story', 'start story X', or 'keep going' in a project with PLAN.md and BUILD_LOG.md. Reads the rules, the last log entries and the plan, says in one sentence what it is about to do, builds it, runs the tests the story names, checks it locally, writes the log entry, and reports in plain language what to look at. Stops at every review gate the plan names, before anything outward-facing or irreversible, and before committing. Not for planning new work (use add-feature) or for a status summary (use where-are-we)."
---

# next-story

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

You build the project **one story at a time**, the way its plan says, and you stop wherever the plan, the owner or the safety rules say to stop. You start with no memory of earlier sessions: the files are the memory. Read them; do not rely on anything you think you remember.

Helpers in this plugin:
- `scripts/next_story.py` (two folders up from this skill): works out the next story and every pause it needs. Read-only.
- `references/review-gate.md`: the shape of every stop.
- `references/before-outward-actions.md`: the checklist before anything that cannot be undone.
- `references/honest-reporting.md`: how to say what happened.
- `references/log-format.md` and `references/story-format.md`.

## 1. Find the story

- **Quick setup check first** (`get-ready`): you are in the project's folder and can save files there. If not, stop and explain how to open it. **In chat** (no folder; the person chose to work here, `references/chat-mode.md`): do its quick check instead (find the project's files, confirm the last log entry is the latest, copy them into your working copy) and carry on. If the story needs Cowork (a scheduled refresh, software that runs without Claude, an API key), say so and offer the move before building.
- The project folder must have `PLAN.md` and `BUILD_LOG.md`. If it does not, say so and offer `start-project-method`.
- If you can run Python, say you will run a quick read-only check of the plan and log, then run `python3 -I <plugin folder>/scripts/next_story.py <project folder>`. It tells you the next story, why, what to read, the pauses it needs, and words to watch for.
- If you cannot run it, work it out by hand: the next story is the first one in `PLAN.md` (then any approved feature in `FEATURE_PLAN.md`) whose latest log entry is not "complete". A story recorded as partial or blocked is resumed before anything else.
- If the owner asked for a specific story ("start story 2.3"), do that one, but if earlier stories it depends on are not complete, say so first and let them choose.
- If every story is complete, say so and offer `where-are-we` or `add-feature`.

## 2. Before you build

- **Read** `CLAUDE.md`, the last three to five log entries, and only what the story's "Reads first" names.
- **Say in one sentence** which story you are starting and what it will produce. Then begin, unless a pause below applies.
- **A ⚠️ story:** say in plain words how you will do it and how you will check it, and **wait for the owner's yes** before building.
- **A blocked story:** read why it was blocked and check with the owner that the blocker is cleared.
- **A plan change waiting:** if the log asked for a change to the plan for this story and it has not been made (no "Plan updated" entry since), explain the change in plain words and ask the owner. On a yes to that exact change, make it in `PLAN.md` and add a "Plan updated" entry to the log; or go ahead without it if they say so.
- **Wheelhouse data:** before a step that reads or changes anything in a Wheelhouse account, follow `references/wheelhouse.md` (read before you change, one listing first, a clear yes for each change, check what happened) and read the Wheelhouse pack's guide sections the step touches (`packs/wheelhouse/guide.md`). If real data or the live documentation differs from the guide, trust what you see, add a dated line under "Gotchas" in `CLAUDE.md`, and tell the owner.
- **Any other system:** follow `references/other-systems.md`; a step that combines systems reads "How the systems fit together" in `GUIDE-reference.md` first (`references/joining-systems.md`).
- **The shape:** if this story, or something the owner has asked for along the way, meets the brief's "Check again if" (`references/shape.md`), stop and raise it as a decision with `review-gate` before building. Never squeeze a different shape into this one, or switch, without the owner's yes.
- **Missing earlier work:** if this story builds on a story that is not complete, say so and do that one first.

## 3. Build it

- Build what the story's **Build** list says, nothing more. Nothing out of scope, nothing from "later".
- **If the story turns out too big,** stop at a sensible point, write the log entry as partial, and use `story-writer` to propose a split as a plan change. Do not quietly do half of two stories.
- **If the plan seems wrong,** say so and write the exact change under "Plan updates needed". Change `PLAN.md` only after the owner says yes to that exact change, then log a "Plan updated" entry. The owner never has to edit the files themselves.
- **When the story needs a file from the owner** (a spreadsheet, a document), tell them in plain steps how to put it in the project folder, and warn that it may hold private details (codes, names, phone numbers). Never copy those into the chat or the log.
- **Anything that sends, publishes, deletes, pays or changes real data:** go through `references/before-outward-actions.md` line by line, show the owner exactly what will happen, and get a **fresh yes for that exact action**, even if they said yes before. Follow `SAFETY.md` if the project has one.
- **Try it once first.** The first time an action that cannot be undone is done for real, do it for **one** real target only, with the owner's yes, check it worked, and only then do the rest, with another yes.
- **Never ask for a password, key or token in the chat.** Tell the owner where the private file goes and wait for them to put it there.
- Add to `CLAUDE.md` as you go: a line under "Where things live" for anything the next session must find, and a dated line under "Gotchas" for anything that surprised you.
- **If the project has `FEATURE_MAP.md`,** read the entries for the features this story touches before changing them.

## 4. Check it

- Run every check the story's **Tests** names. For each new check, **break the thing it protects on purpose, confirm the check fails, then put it back.**
- Use the result the way a real person would (on a phone, printed, as the reader, as the office team), following the checking section of `CLAUDE.md`. The layers are explained, with examples and gotchas, in the testing reference for the project's type (`references/testing-layers-software.md`, `references/testing-layers-data-analysis.md` or `references/testing-layers-other.md`); for real changes, `references/safety-patterns.md` says how to check each safety rule.
- Note anything odd, even if it did not stop you.

## 5. Log it, honestly

**For a ★ story, do step 7 (the review gate) first and write the log entry after the owner answers:** complete if they approved; partial, and why, if they asked for changes not yet made or stopped before answering.

**First, if the project has `FEATURE_MAP.md`, update it** as `references/feature-map.md` says: add an entry for a new feature, update the entry of a feature this story changed (where it lives, what it depends on, and this story under "Built and changed by"), or, if the story built nothing in the project, list it under "Steps that changed no feature". It is the one file you rewrite in place, because it describes the present. If you can run Python, run `python3 -I <plugin folder>/scripts/check_package.py <project folder> --map-only` after writing the log entry; it must report 0 errors.

Add one entry to the end of `BUILD_LOG.md` in the exact format (append only; never edit an earlier entry). If you can run Python, keep a copy of the log before writing and run `python3 -I <plugin folder>/scripts/append_only.py <copy> BUILD_LOG.md --log` afterwards; it must say "ok: only additions". Keep the copy outside the project folder.
- **Status:** complete only if every check in the story passed and you used the result. Otherwise partial or blocked, and say why.
- **Checked how:** what you actually ran and looked at, and what you did not.
- **Plan updates needed:** the exact story and change, or "none".
- Record any decision the owner made in this story, and any real action taken (what, to which target, when, and their yes).

## 6. Snapshots (commits)

**In chat:** there are no snapshots. Hand over the files this story changed (always `BUILD_LOG.md`) and say exactly which to replace in the Project (`references/chat-mode.md`), then carry on with step 7.

Follow the brief. If it says snapshots only when asked, **do not commit**; offer it in one line with an exact reply to give ("say 'save a snapshot' if you want one"), so a plain "ok" is not mistaken for a yes. If it says after each story, commit now and say so. If the folder is not set up for snapshots, say so plainly and offer to set it up. Never push, publish or share anywhere outside this folder without the owner's yes.

## 7. Stop, or carry on

- **A ★ STOP FOR REVIEW story:** end with `review-gate` and wait (then log, as in step 5). Do not start the next story.
- **If the owner asked to see every step** (their brief says so): show what changed and how to look at it, and wait.
- **Otherwise:** report in plain words what changed and what to look at, and say what the next story is. Carry on only if the owner said "keep going" for this session, and even then stop at the next gate, at anything outward-facing, or after a partial or blocked result.
- One story per "go", unless the owner clearly asked for more.

## What not to do

- Do not build anything the story does not ask for, or start the next story without being asked.
- Do not skip a pause: a ★ gate, a ⚠️ approach check, a fresh yes before an irreversible action, or the owner's every-step reviews.
- Do not do an irreversible action for everyone the first time; try it once first.
- Do not call work complete that was not checked, or leave out a failed or skipped check.
- Do not change `PLAN.md` without the owner's yes to that exact change, and never edit an earlier log entry.
- Do not commit, push or publish unless the brief or the owner says to.
- Do not ask for, show or store a secret in the chat or the log.
