---
name: where-are-we
description: "Tells the user where a project stands, in plain language: what is done, what is next, what is waiting on them, and any open decisions. Use at the start of a cold session, or when the user asks 'where are we', 'what's the status', 'catch me up', 'what did we decide', or 'what's left'. Reads the rules, plan and build log (including files the user has edited by hand) and changes nothing."
---

# where-are-we

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

You tell the owner, in a few plain sentences, where their project stands. You **read only**: you change no file, start no story and make no decision. This is the first thing to do in a session that starts cold.

Helper: `scripts/project_status.py` (two folders up from this skill). It reads the package, copes with hand-edited and missing files, and uses the build runner's own logic for "what's next", so the two always agree.

## 1. Read

- **Quick setup check first** (`get-ready`): if you cannot see a folder on the person's computer (a plain chat or the phone app), look for the project's files in the Claude Project or attached to the message and read those (`references/chat-mode.md`; say which last log entry you see and ask whether it's the latest). If there are none, say so, and explain how to open the project's folder in Cowork or add the files here.
- If you can run Python, say you will run a quick read-only check, then run `python3 -I <plugin folder>/scripts/project_status.py <project folder>`.
- Otherwise read the files yourself: the brief (project, owner, type, size, open questions), `PLAN.md` (the stories), `FEATURE_PLAN.md` if it exists (the index and its statuses), and `BUILD_LOG.md` (each entry's story and status, the latest entry's plan changes).
- The owner may have edited files by hand. Be tolerant of small differences (a missing bracket, a different dash, a capital letter), and say plainly if something cannot be read rather than guessing.
- **Notes the owner added to the log** (a dated line with no story and no status, such as "note: staff start at 9 now") are not sessions: mention each one, and say whether it affects the plan.
- **If the helper's summary seems to disagree with what the log actually says,** trust the log, tell the owner what you found, and mention the difference.

## 2. Tell them, in this order

1. **The project in one line:** its name, the kind and size of plan, and what it connects to (from the brief's systems line and any feature that added a system; `references/scope.md`), in plain words: "uses your Wheelhouse data and Guesty"; and how it is used and kept up to date (the brief's shape, `references/shape.md`), plus any shape decision waiting on them.
2. **What is done:** how many stories of the plan are complete, and any features done.
3. **The last session:** when, which story, and how it ended (complete, partial, blocked).
4. **Waiting on you:** anything that needs the owner: a review gate they have not answered, a feature waiting for their review, a plan change waiting for their yes, a blocked story, open questions from the brief not yet answered, a deadline that has passed or that the plan no longer fits. Lead with this if there is anything.
5. **What is next:** the next story, in one line.
6. **What to say next:** "What's next?" to build it, "Let me review" to look first, or "I want to add…" for a new idea.

Keep it short: a handful of lines. Offer more detail only if asked ("what did we decide about…" → look it up in the log and the decisions table and quote it).

## Special cases

- **No project here:** say so, and offer `start-project-method`.
- **The interview is in progress** (the brief starts with "Interview progress"): say where it got to, and offer to continue.
- **Package files missing:** name them, and offer to rebuild the package from the brief with `generate-package` (which never overwrites the log).
- **Everything is done:** say so, mention anything still waiting on the owner, and offer `add-feature`.
- **A log entry with no readable status:** say it was not counted, so the owner can fix it if it matters.

## What not to do

- Do not change any file, or start a story, from here.
- Do not guess a status the files do not show.
- Do not bury what is waiting on the owner.
- Do not repeat the whole log; summarize, and quote only what is asked for.
