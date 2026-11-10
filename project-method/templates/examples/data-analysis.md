# Worked example: data and analysis (an invented project, "Branch Visits Review")

Use this as a model for what good stories look like. It is not a template to copy: write stories from the user's own brief.

**The brief in one line:** an analysis of which library branches are busiest, and when, to help the board decide opening hours. It only reads spreadsheets.

**Why the stories look like this:** the definitions are written and approved before any number exists; every figure is checked against a hand-worked sample and an independent source; the results always say what was and was not checked.

### Story 0.1 ★ STOP FOR REVIEW — Write down the question and the definitions

**Reads first:** `PROJECT_BRIEF.md`.

**Build:**
- The exact question in one sentence, and who will act on the answer.
- A plain-words definition of "visit", "busy hour" and "typical day": what is counted, over what period, and what is left out (for example, closed days).
- The list of sources and what each is trusted for.

**Tests:** the owner reads each definition and says it means what they meant; any word with two possible meanings has been split into two measures.

**Done when:** the owner has approved the definitions in writing.

**Prompt:**
```
Read PROJECT_BRIEF.md. Write the exact question, a plain-words definition of visit, busy hour and typical day (what is counted, over what period, what is excluded), and the list of sources. Produce no numbers. Stop for review and ask the owner to confirm each definition.
```

### Story 1.2 — Check that each branch's spreadsheet holds what we think it holds

**Reads first:** `GUIDE-reference.md`, the approved definitions.

**Build:**
- For each branch, the first and last date present, any missing months, and how closed days appear (blank, zero, or absent).
- A short list of surprises and what each could do to the answer.

**Tests:** the counts of rows and dates are reproduced by a second method; break one input on purpose (delete a month) and confirm the missing-month check notices.

**Done when:** every difference between branches in how they count is written down and the owner has said how to treat each.

**Prompt:**
```
Read GUIDE-reference.md and the approved definitions. Read each branch's spreadsheet without changing it, and report its first and last date, missing months, and how closed days appear. Reproduce the counts a second way. Break one input on purpose to prove the missing-month check works, then restore it. List every surprise and what it could do to the answer. Do not clean or alter the data. Log it and stop.
```

### Story 2.2 ⚠️ — Produce the busiest-hours figures and prove them

> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here): The board will act on these numbers, and a wrong figure looks exactly like a right one.

**Reads first:** the approved definitions, the pinned sample from story 1.3, the log entries so far.

**Build:**
- Visits by branch, weekday and hour for two years, using only the approved definitions.
- A hand-worked sample for one branch and one week, reproduced exactly.
- A reconciliation against an independent source (the branch's own monthly total), with every difference explained.

**Tests:** the sample matches exactly; monthly totals match the independent source or the gap is explained line by line; a deliberately double-counted row changes the result and is caught.

**Done when:** every figure handed over has a note of how it was checked and what it cannot tell us.

**Prompt:**
```
Read the approved definitions, the pinned sample and the log. Produce visits by branch, weekday and hour using only the approved definitions. Reproduce the hand-worked sample exactly, reconcile monthly totals with each branch's own total and explain every difference, and prove the double-count check by double-counting one row on purpose and restoring it. Next to each figure write how it was checked and what it cannot tell us. Log it and stop for review.
```
