---
name: generate-package
description: "Turns a confirmed Project Brief into the project package: START-HERE, rules (CLAUDE.md), plan with stories and paste-ready prompts, build log, and any guides the project needs, sized Lite, Standard or Full and shaped for the project type (software, data and analysis, or other). Use after the `start-project-method` skill, or when the user says 'generate the plan', 'create the project files', 'rebuild the package from the brief', or the brief has changed. Shows the plan outline and waits for a yes before writing story prompts. Never leaves blank placeholders."
user-invocable: false
---

# generate-package

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

You turn the owner's confirmed `PROJECT_BRIEF.md` into their **project package**: the files that let any later session pick the project up cold and build it one reviewed story at a time. You write files; you do **not** start building the project.

What you need:
- The templates and their map: `templates/manifest.json` and the files beside it. How the template markers work is in `templates/README.md`.
- How to write a good story: `references/story-format.md` (and the `story-writer` skill). One worked example per project type: `templates/examples/software.md`, `templates/examples/data-analysis.md`, `templates/examples/other.md`. Use them as models, never copy them.
- The checker you run at the end: `scripts/check_package.py` (in this plugin's `scripts` folder, two folders up from this skill).

## 1. Check the brief first

- **Quick setup check** (`get-ready`): you are in the project's folder and can save files there. If not, stop and explain how to open it. **In chat** (no folder; the person chose to work here, `references/chat-mode.md`): do its quick check instead (find the project's files, confirm the last log entry is the latest, copy them into your working copy) and carry on. Write the package into your working copy.
- It must be **confirmed**: a line "Confirmed by <owner> on <date>", and no "Interview progress" line. If it is not, stop and offer to finish the interview with `start-project-method`.
- Every field must have a real answer (defaults like "None yet" are fine; "Not answered yet" is not). If one is missing, ask the owner that one question, then continue.
- Keep the confirmed brief as it is. The one exception: if **Type of project** or **Size of the plan** has extra words after the type or size, move the extra words to **Why this size** (or drop them), and tell the owner you only tidied the format.
- **Safety floor:** if "Can it change anything real" starts with "yes", the size must be Standard or Full. If the brief says Lite, stop, explain in one sentence why it must be Standard (room for the safety steps), and ask the owner to agree before going on.
- If a package already exists here, read "Regenerating" below before writing anything.

## 2. Work out which files to write

Use `templates/manifest.json`: every entry whose types include the project type and whose sizes include the size, plus `SAFETY.md` only when the project can change something real. Never include `FEATURE_PLAN.md` in a first package (the `add-feature` skill creates it later). In practice:

- **Every package:** `START-HERE.md`, `PROJECT_BRIEF.md` (keep the owner's confirmed brief as it is), `CLAUDE.md`, `PLAN.md`, `BUILD_LOG.md`.
- **Standard and Full add:** `GUIDE-glossary.md`; for software `GUIDE-design.md`, `GUIDE-reference.md` and `FEATURE_MAP.md` (written as the template stands: it fills in as stories are built; see `references/feature-map.md`); for data and analysis `GUIDE-reference.md`; for other projects `GUIDE-house-style.md`; and `SAFETY.md` when it can change something real.

## 3. Show the plan outline and wait (review gate)

Before writing any detailed story, show the owner, in plain words (use the explanations in `references/glossary.md`; never use a term like "doorway", "sandbox" or "commit" with the owner; say "one safety check every message goes through", "a test copy", "a saved copy"). **Keep it to one screen:** the phase names and the story titles, one line each, nothing else; offer details if they want them:
- the size and the reason (from the brief);
- the phases, and under each, the story titles in order, one line each, with ★ on the stories that stop for their review and ⚠️ on the ones that need extra care;
- which open questions get their own early story;
- if the brief has a deadline, whether the plan fits it. A rough rule: count the working days until the deadline; if there are more stories than working days, or fewer than two days per review stop, it probably does not fit. Say so plainly and offer the choices: move the date, trim the scope, or a smaller first version.

Then ask: "Does this look right? Anything to add, move or drop?" **Do not write the detailed stories until the owner says yes.** Make the changes they ask for and show the outline again if it changed much.

### How to shape the outline
- **Keep Story 0.1 and Story 0.2 from the template** for the project type. They are always first: set-up (software), definitions (data), or outline (other); then answering the open questions.
- **Cover every in-scope item** with at least one story. Nothing out of scope; nothing from "later".
- **Open questions:** all are listed in the plan and answered in Story 0.2. Give a question its own early story when later work depends on the answer.
- **Each connection** to an outside system or source gets an early "check it holds what we think" story that fills in `GUIDE-reference.md`: read-only, or, for a service that only sends, using its test mode and its own documentation, sending nothing.
- **Software:** Story 0.1 asks the owner to choose how it is built and where it runs (★). A first look on made-up data comes early, as a ★ story, before any real data or connection. Real data replaces made-up data in its own stories. If people will use it on their own phones or computers, putting it online is its own story near the end (★ ⚠️, reads `SAFETY.md` if the project has one), treated like a first real action: tried privately first, then opened to one real user, then everyone.
- **Data and analysis:** definitions first and approved (★); numbers are proved against a hand-worked sample and an independent source (⚠️).
- **Other:** outline approved (★), then a complete draft, then dated review rounds, then a final check where it will really be seen. The hand-over delivers the finished piece in the format the owner can open and print (ask which: a Word file, a PDF, printed pages), not only as the working files.
- **Checks:** each story's Tests come from the testing reference for the type (`references/testing-layers-software.md`, `references/testing-layers-data-analysis.md`, `references/testing-layers-other.md`), as much as the size calls for; a project that changes something real follows `references/safety-patterns.md`.
- **The scope** (the brief's systems line; `references/scope.md`) decides what else goes in:
  - **Wheelhouse:** follow `references/wheelhouse.md` and the Wheelhouse pack (`packs/wheelhouse/README.md`): its seven rules go into `CLAUDE.md` (and `SAFETY.md` if the project changes things), the facts the project needs from the pack's guide go into `GUIDE-reference.md` under "Wheelhouse" with the date each was checked, and the pack's stories go in where its `stories.md` says (A always; B if it is software that runs without Claude; E if it is a page a team uses; C and D if it changes anything), and the first story that touches Wheelhouse only reads. How it gets its data follows the brief's shape (`references/shape.md`; guide §2).
  - **Any other system:** follow `references/other-systems.md`: its early read-only story fills that system's section of `GUIDE-reference.md` (its documentation, how it signs in, its limits, what its data really holds).
  - **More than one system together:** follow `references/joining-systems.md`: a matching story (★ ⚠️) after each system's own read-only story, and "How the systems fit together" in `GUIDE-reference.md`.
  - A project with no systems gets none of these.
  - Lite has no `GUIDE-reference.md`: if a Lite project uses a system, write what the early story finds under "Where things live" and "Gotchas" in `CLAUDE.md` instead.
- **The shape** (the brief's "How it will be used and kept up to date"; `references/shape.md`): the stories build that shape and no other. Its line and "Check again if" go into `CLAUDE.md` and the plan's decisions table (the templates have the places). A plan in tiers 1 and 2 (everything except software that runs without Claude) ends with a short "When you outgrow this" note: the signals from "Check again if" and what the next tier would add, with no stories for it.
- **Anything that changes something real:** a story that builds the single checked doorway and tries it on a test copy (⚠️, reads `SAFETY.md`), then a separate story for the first real change, with a fresh yes from the owner (★ ⚠️). Never put the first real change inside a bigger story.
- **Mark the stories** with ★ STOP FOR REVIEW where a person must look before more is built on it (the first look at anything visual, a sample document, first results, a definition numbers rest on), and with ⚠️ (needs extra care, with a one-sentence reason) where a quiet mistake would be costly. See `references/story-format.md`.
- **Files the owner provides:** when a story needs a file from the owner (a spreadsheet, a document), say in plain steps how to put it in the project folder, and warn that it may hold private details (codes, names, phone numbers) that must not be copied into the chat.
- **Size:** Lite has eight stories or fewer and no phases (number them 1.1, 1.2, … in order after 0.1 and 0.2). Standard usually has eight to twenty, in phases. Full has more phases and more review stops: a review gate before each outward-facing story, and a reference section per connected system. If a Lite outline grows past eight stories, say so and offer Standard.
- **Last:** a full walk-through or final read, then a hand-over story (how the owner, or whoever runs it, uses it from now on).
- Respect the owner's pauses and snapshot choice from the brief.

## 4. Write the files

For each file, start from its template and follow the markers exactly (`templates/README.md`):
- Fill every `{{placeholder}}` with the owner's real answer from the brief, in their words. `{{today}}` is today's date. `{{phases_heading}}` is "Order of work" for Lite and "Phases" for Standard and Full.
- Keep a block only when its condition matches (project type, size, and whether it can change something real). Remove the markers themselves.
- Insert included parts where the template says to.
- Remove every `note:` and `example:` comment. They are guidance for you, never for the owner.
- In `PLAN.md`, replace the stories section with the real stories, written with `story-writer`, keeping Stories 0.1 and 0.2 first. Adapt them to the project (what the definitions or outline cover, the file they write) but keep their shape, their review gate and their checks. For Standard and Full, number stories by phase (1.1, 1.2, 2.1, …); for Lite, simply in order.
- In the guides, write in what the brief already tells you (the feel, the devices, the systems, the words); leave the template's "filled in later" notes only for what nobody knows yet. For Wheelhouse, write in the pack's guide facts the project needs; for any other system, the links to its documentation if known.
- **Leave nothing blank.** If something has no answer, say so in plain words ("None yet"). A delivered file must contain no `{{` and no comment markers.
- Every file "Reads first" names must exist in this package.

- **Write `BUILD_LOG.md` last,** in step 5 between the two checks, so its first entry states the real result: `{{package_files}}` is the list of files you wrote, and `{{package_check}}` is what the check found (for example "scripts/check_package.py: 0 errors, 0 warnings", or the by-hand checklist and anything you could not check).

## 5. Check it

If you can run Python, tell the owner you will run a quick read-only check of the files, then:
1. Before writing the log, run `python3 -I <plugin folder>/scripts/check_package.py <project folder> --before-log`. Fix every ERROR and run it again until there are none. Read each WARNING and fix it unless it is clearly fine.
2. Write `BUILD_LOG.md`, with the real result in its first entry (and any warning you left, with the reason).
3. Run the full check (without `--before-log`). It should be clean. If it finds a problem in the entry you just wrote, correct that entry before handing over; it is the first entry and nothing builds on it yet.

If you cannot run it, check by hand: the right files exist for the type and size; no `{{` or comment markers remain; every story has Reads first, Build, Tests, Done when and a ready-to-paste Prompt; Stories 0.1 and 0.2 are kept; at least one ★ story; every ⚠️ story says why; if it can change real things, a ⚠️ story reads `SAFETY.md`; every open question from the brief appears in the plan; every file a story reads exists; the log has its format and a dated first entry.

## 6. Hand it over

Tell the owner, in plain words and in about five lines:
- which files now exist and what each is for (one line each; `START-HERE.md` says the same);
- what was checked and how, honestly, including anything not checked;
- what happens next: say *"What's next?"* to start the first story, or *"Where are we?"* in any later session.

**In chat:** hand over every file you wrote, for download, and tell them to add them all to the Project's files (`references/chat-mode.md`); say it is the one time they add everything at once.

The first log entry (from the template) records that the package was created. Do not commit or share anything unless the brief says snapshots are saved automatically or the owner asks.

## Changing the brief

When the owner wants to change what the project is (who it is for, what is in or out, the deadline, whether it can change something real):
- **A new thing the owner wants** (something not in the brief) becomes a feature with `add-feature`, at any stage. If no story beyond 0.1 and 0.2 is complete and the owner would rather fold it into the brief and rebuild the plan, offer that choice in one line and let them pick.
- **A correction to the brief before any story beyond 0.1 and 0.2 is complete:** go through the change with the owner in plain words, say it back, and get a clear yes. Update `PROJECT_BRIEF.md` (keep the "Confirmed by" line, and add a line under it: "Changed on <YYYY-MM-DD>: <what changed>, confirmed by <owner>"), add a "Brief changed" entry to the log, then regenerate as below.
- **A correction once building has started** becomes a proposed plan change, made after the owner's yes and logged as "Plan updated".
- If the change makes the project able to change something real, the safety floor applies (Standard or Full, a `SAFETY.md`, the safety stories).

## Regenerating

When the brief has changed and the package already exists:
- **Never overwrite or shorten `BUILD_LOG.md`.** Add a new entry saying the package was regenerated, from what change in the brief, and what changed in the files.
- **Never undo finished work.** Stories already marked done in the log keep their place and numbers; change only stories not yet started.
- **Keep what the owner decided.** Carry every row of the plan's decisions table and every change the owner approved into the new `PLAN.md`, word for word. Regenerating counts as a plan change: it needs the owner's yes below.
- Show the owner the list of files you will rewrite and what changes in each, and **wait for a yes** before writing.
- If `FEATURE_PLAN.md` exists, leave it alone.

## What not to do

- Do not generate from an unconfirmed brief, or invent an answer the brief does not give.
- Do not write detailed stories before the owner has approved the outline.
- Do not make a project that can change real things Lite.
- Do not start building, run the project, or change anything outside the package files.
- Do not leave placeholders, comment markers, or files a story points at but the package lacks.
- Do not overwrite the log or any finished work when regenerating.
- Do not include anything from the worked examples' invented projects in the owner's package.
