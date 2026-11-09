---
name: review-gate
description: "The standard way to stop and hand a decision to the user: summarize what exists, show how to look at it (a link, a screenshot, a file path), list the decisions needed with a recommendation for each, and wait. Used by the other skills at every pause; also use it when the user says 'let me review', 'pause here', 'show me before you continue', or when a story is marked STOP FOR REVIEW. Never proceeds past a gate without an explicit yes."
user-invocable: false
---

# review-gate

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

A review gate is where the owner steers. You stop, you show them what exists and how to look at it, you tell them honestly what was and was not checked, you ask for the decisions you need with a recommendation for each, and **you wait**. Nothing further is built until they answer. The full shape, with an example, is in `references/review-gate.md`; how to report honestly is in `references/honest-reporting.md`.

## When

- At the end of every story marked **★ STOP FOR REVIEW**.
- After the brief (in `start-project-method`) and after the plan outline (in `generate-package`).
- After every story, if the owner's brief says they want to see every step.
- Before any action that sends, publishes, deletes, pays or changes real data (with the checklist in `references/before-outward-actions.md`).
- Whenever the owner says "let me review", "pause", "show me first", or something unexpected happens that they should know about.

## What to say, in this order

1. **What now exists**, in one to three plain sentences.
2. **How to look at it**: exactly what to open, where, and what to try (in chat, the file you just shared for download, `references/chat-mode.md`). Never just "have a look". It must be something the owner can actually do, on the device they use (their phone, if that is all they use): a screenshot, a link that opens on their phone, a printed page, a file that opens with a double-click. Never a command to type, unless they have said they are comfortable with that.
3. **What I checked, and what I did not.** Name any failed, skipped or impossible check.
4. **Decisions I need from you**: a short numbered list; each with my recommendation and the reason in one line. Say what happens if they don't answer only when waiting is harmless; for anything that cannot be undone there is no default.
5. **Then wait**, saying what reply moves things on ("Reply with your answers, or 'go' to accept my recommendations").

Keep it short enough to read on a phone. Plain words only.

## Waiting

- **Only a clear yes to this gate moves on:** "yes", "go", "looks good, carry on", or answers to the questions asked.
- **Not a yes:** silence, a question back, "maybe", a reply about something else, or a yes given earlier for a different step.
- **A bare "ok"** counts as a yes only when the gate asked one yes-or-no question and nothing in it cannot be undone. Otherwise ask, in one line, "Is that a yes to <the specific thing>?"
- For an action that cannot be undone, the yes must be to that exact action, with the target in front of the owner.
- If they ask for changes **that fit the story** (its Build list and the brief's scope), make them as part of the same story, then show the gate again.
- If they ask for something **beyond the story or the brief's scope**, say so plainly and let them choose: a proposed plan change (made after their yes and logged as "Plan updated"), a new feature (`add-feature`), or "later". Do not slip it into the current story.
- If they want to stop for now, write the log entry (partial if the story is not finished) and tell them how to pick up: say "where are we?" next time.

## Record it

For a story that ends at a gate, write its log entry **after** the owner answers, with their decisions in it (complete if they approved, partial if not yet). If a decision changes the plan, write the exact change under "Plan updates needed"; make it in `PLAN.md` once the owner says yes to it, and log a "Plan updated" entry.

## What not to do

- Do not continue past a gate because the answer seems obvious.
- Do not ask more than a handful of questions at once, or bury the important one.
- Do not present unchecked work as checked.
- Do not treat an old yes as covering a new action.
