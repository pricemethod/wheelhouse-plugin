---
name: add-feature
description: "Adds a new feature or idea to a project that already has a package, without rewriting history: clarifies what the user wants, writes a new feature section and its stories into FEATURE_PLAN.md (append-only), and stops for review before anything is built. Use when the user says 'I want to add', 'new feature', 'we should also', 'next idea', or brings an idea after the first build is done. Records scope decisions (what is in, what is deferred) in the plan and log."
---

# add-feature

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

The owner has a new idea for a project that already has a package. You turn it into a **feature**: a short written section with its own stories, added to `FEATURE_PLAN.md`. You **do not build anything** here: the owner reviews the feature first, and the build happens later with `next-story`, one story at a time.

What you need:
- The shape of a feature section and its index row: `references/feature-section.md`.
- The template for a new feature plan: `templates/FEATURE_PLAN.md`.
- How to write each story: `story-writer` and `references/story-format.md`.
- The checker that proves you only added text: `scripts/append_only.py` (two folders up from this skill).

## 1. Look first

- **Quick setup check first** (`get-ready`): you are in the project's folder and can save files there. **In chat** (no folder; the person chose to work here, `references/chat-mode.md`): do its quick check instead (find the project's files, confirm the last log entry is the latest, copy them into your working copy) and carry on. When the feature is written, hand over `FEATURE_PLAN.md` and `BUILD_LOG.md` and say to replace them in the Project.
- The folder must have a package (`PLAN.md`, `BUILD_LOG.md`, a confirmed `PROJECT_BRIEF.md`). If it does not, offer `start-project-method` instead.
- Read the brief, the rules file, the last few log entries, the plan's decisions table, `FEATURE_PLAN.md` if it exists, and `FEATURE_MAP.md` if it exists (what is built now and where; see `references/feature-map.md`). Know what is already built so you do not plan it again.
- **If the idea is already in the plan** (a story not yet built), say so and offer to carry on with `next-story` instead.
- **If the idea is in the brief's "out of scope"**, say so kindly; it can still become a feature, but the owner must decide that, and the decision is written down.

## 2. Clarify, briefly

Ask only what you need to write the section: what they want, who it is for, what "done" looks like, what is deliberately not included, and anything it connects to or changes in the real world. If it brings in a system the project doesn't use yet, or starts changing something it only read before, the scope changes: follow "When it changes" in `references/scope.md`, say the matching plain sentence, and add the early stories that system needs (the Wheelhouse pack's `stories.md`; `references/other-systems.md`; the matching story in `references/joining-systems.md`). A few questions at a time, plain words, examples offered, "I don't know" accepted (record it as an open decision). Say it back in a sentence and check you have it right. If it is really two ideas, say so and make two features.

**Check the shape** (`references/shape.md`): compare the idea with the brief's "Check again if". If it meets one (it has to update itself, people outside Claude need it, it feeds another system), stop before writing the feature and raise it as a decision with `review-gate`: what the idea needs, why the current shape can't do it well, the choices (do it within the shape another way, or change the shape) and what changing costs, with a recommendation. Write the feature only for the shape the owner chooses, and record the decision.

## 3. Write the feature (append only)

- **If `FEATURE_PLAN.md` does not exist,** create it first from `templates/FEATURE_PLAN.md`: fill the placeholders from the brief, remove the markers and notes, leave nothing blank.
- **Then, before adding the feature,** keep an exact copy of the file as it is now, outside the project folder (for the check in step 4).
- **Add, never rewrite:**
  - a row to the index: `| <n> | <name> | F<n>.1–F<n>.<last> | Draft, waiting for the owner's review |`;
  - any scope decision, dated, to the scope-decisions table ("Only rates for now; other overrides stay as they are");
  - any "later" idea the owner mentions, to the backlog;
  - the feature section at the end, in the shape in `references/feature-section.md`: what was asked for (in their words), the goal, what already exists (from `FEATURE_MAP.md` where there is one: the features this one builds on or changes, by name), in scope, out of scope, decisions with a recommendation each, and the stories.
- **Number** features in order and their stories `F<n>.1`, `F<n>.2`, … so they never collide with the plan.
- **Write each story with `story-writer`:** all seven parts, ★ where the owner should look before more is built, ⚠️ with a reason where a quiet mistake would be costly. A feature that changes anything real gets the same safety stories as the main plan: the doorway tried on a test copy, then the first real action done once, for one target, with a fresh yes.

## 4. Prove you only added things

If you can run Python, run `python3 -I <plugin folder>/scripts/append_only.py <your copy> FEATURE_PLAN.md --feature-plan`. It must say "ok: only additions". If it does not, put back what you changed and add your text instead. If you cannot run it, compare by eye: every earlier line is still there, unchanged and in the same order; the only line that may differ is the Status cell of a feature's index row.

## 5. Stop for review (the feature review gate)

Use `review-gate`, with all five of its parts: what now exists (the feature section, and where it is in `FEATURE_PLAN.md`), how to look at it, what you checked (including the append-only check) and what you did not, the decisions you need with a recommendation each (the goal, what is in and out, anything open), and the story titles with ★ and ⚠️, explained in plain words. Then wait.

- **On a clear yes:** change only that feature's Status cell to `Approved <today's date>`, and run the append-only check again against your copy. Only now can `next-story` build it.
- **If they want changes:** make them in the feature's own section (it has not been approved or built, so it is still a draft), show it again, and wait.
- **If they decide not to do it:** leave the section, change the Status cell to `Dropped <date>`, and record why in the scope decisions.

## 6. Log it

Add one entry to `BUILD_LOG.md` (append only), headed `## [<YYYY-MM-DD>] Feature <n> added — <name>`: the feature added, the owner's decisions and scope calls in their words, whether it was approved, and what you checked (including the append-only check). If you can run Python, prove the log only grew too: keep a copy before writing and run `python3 -I <plugin folder>/scripts/append_only.py <copy> BUILD_LOG.md --log`.

## What not to do

- Do not build, run or change anything outside `FEATURE_PLAN.md` and the log.
- Do not delete or reword anything already in `FEATURE_PLAN.md`, the plan or the log. Once a feature is approved, its section only grows too: changes become a new dated note under it, or a new feature.
- Do not mark a feature Approved without the owner's clear yes.
- Do not squeeze a new idea into the main plan's stories.
- Do not leave a scope decision unwritten.
