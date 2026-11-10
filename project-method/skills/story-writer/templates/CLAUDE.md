# CLAUDE.md — {{project_name}}

{{one_liner}}

This file holds the rules that are true in **every** session. The detail of what to build lives in `PLAN.md`; the history of what has happened lives in `BUILD_LOG.md`; what the project is for lives in `PROJECT_BRIEF.md`. Read this file first, every time.

## Read before starting any story
- `PLAN.md` — find the next open story, its "Reads first" list and its prompt.
- `BUILD_LOG.md` — skim the last three to five entries so a recent decision is not silently reversed.
<!-- if: size=standard,full -->
- The `GUIDE-*.md` files — only the sections the story points to, not the whole file each time.
<!-- /if -->
<!-- if: type=software; size=standard,full -->
- `FEATURE_MAP.md` — what is built now and where: find the features this story touches before changing them.
<!-- /if -->
- `PROJECT_BRIEF.md` — when a question about purpose, audience or scope comes up.

Each session starts with no memory of the last one. These files are the only continuity that exists.

## Who and what this is for
- **For:** {{audience}}
- **Success looks like:** {{success_definition}}
- **How it is used and kept up to date:** {{shape}}
- **Check again if:** {{shape_switch_if}}. Whenever a story or a new idea meets one of these, stop and raise it with the owner as a decision (keep the shape, or change it and what that costs). Never switch, or carry on past it, silently.

## How we work together
- **Pauses:** {{review_cadence}}
- **Saving snapshots (commits):** {{commit_policy}}

<!-- include: parts/house-rules.md -->

<!-- include: parts/review-gates.md -->

## Before finishing any story
Add an entry to `BUILD_LOG.md` (append only) in this exact format, and check the work before writing it:

<!-- include: parts/log-format.md -->

## Scope: what we are and are not doing
- **In:** {{in_scope}}
- **Out (do not build, even if it seems helpful):** {{out_of_scope}}
- **Later (parked):** {{later_ideas}}

## What must never happen
{{never_events}}

<!-- if: type=software -->
<!-- include: parts/testing-software.md -->
Commands for running and checking this project are added here by the first story, then kept current.
<!-- /if -->
<!-- if: type=data-analysis -->
<!-- include: parts/testing-data.md -->
<!-- /if -->
<!-- if: type=other -->
<!-- include: parts/testing-other.md -->
<!-- /if -->
<!-- if: size=lite -->
**How much of this a small project needs:** breaking each new check on purpose, using the result for real, and an honest log entry, always; the other checks when a story's rule, numbers or data call for them.
<!-- /if -->
<!-- if: size=standard -->
**How much of this the project needs:** every check above as soon as a story touches it, with the pinned sample and the independent comparison whenever numbers or real data matter.
<!-- /if -->
<!-- if: size=full -->
**How much of this the project needs:** every check above, for every story it applies to, including a real device or a real reader before any story that people will see is called finished.
<!-- /if -->

<!-- if: size=lite -->
## Look, feel and words
{{look_and_feel}}

## Special words
{{key_terms}}

<!-- /if -->
## Where things live
- This file: the rules. `PLAN.md`: the stories. `BUILD_LOG.md`: the history. `PROJECT_BRIEF.md`: the purpose.
<!-- if: size=standard,full -->
- `GUIDE-*.md`: reference notes for this project.
<!-- /if -->
<!-- if: type=software; size=standard,full -->
- `FEATURE_MAP.md`: every feature, the files it lives in, what it depends on, and the steps that built or changed it. Update it at the end of every story, before the log entry.
<!-- /if -->
- Add a line here whenever a story creates something the next session needs to find.

## Gotchas learned so far
*(None yet. Add one line each time something surprising goes wrong, with the date.)*

## Don't
- Don't build anything listed under "Out of scope", or start a "Later" idea, without a recorded decision.
- Don't change `PLAN.md` without the owner's yes to that exact change; propose it under "Plan updates needed" first, then log a "Plan updated" entry.
- Don't skip the log entry, even for a partial or blocked session.
- Don't mark a story complete without having actually checked it.
- Don't ask the owner to paste a password, key or token into the chat.

---
*Owner: {{owner_name}}.*
