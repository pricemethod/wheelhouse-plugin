# The shape of a feature section

`add-feature` appends one of these to the end of `FEATURE_PLAN.md` for each new feature, adds a row to the index, and adds any scope decision to the scope-decisions table. Nothing already in the file is deleted or reworded. Features are numbered in order (Feature 1, Feature 2, …) and their stories `F<feature>.<number>` (F1.1, F1.2, … F2.1, …), so they never collide with the plan's stories.

## The index row

`| <n> | <feature name> | F<n>.1–F<n>.<last> | Draft, waiting for the owner's review |`

When the owner approves the feature, change only the Status cell to `Approved <date>`. When its last story is complete, change it to `Done <date>`. (The build runner only starts stories of features marked Approved.)

## The section

```
## Feature <n>: <name>

**Asked for (<date>):** the owner's own words, numbered if there are several things.

**Goal.** One or two sentences: who can do what afterwards.

**What already exists** that this builds on (files, stories, decisions), so nothing is rebuilt.

**In scope for this feature:** a short list.

**Out of scope for this feature:** what we are deliberately not doing, so it is not added by accident.

**Decisions** (each with a recommendation and the default if unanswered; nothing irreversible has a default):
1. ...

### Story F<n>.1 — <name>
... (the usual story shape: Reads first, Build, Tests, Done when, Prompt; ★ and ⚠️ as in story-writer)
```

## Rules

- **Clarify first.** Ask only what is needed to write the section (a few questions at a time, plain words, "I don't know" accepted), then write it.
- **One feature, one section.** If the idea is really two features, write two.
- **Stop for review.** Show the owner the section (goal, scope, decisions, story titles with ★ and ⚠️) and wait. Mark it Approved only on their clear yes.
- **Scope decisions are written down** in the scope-decisions table with the date, in plain words ("Rates only for now: other overrides stay as they are").
- **Later ideas** the owner mentions go to the backlog, not into the feature.
- **The safety rules still apply:** a feature that changes something real gets the same doorway, test copy, try-it-once-first and fresh-yes stories as the main plan.
