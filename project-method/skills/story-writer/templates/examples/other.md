# Worked example: other projects (an invented project, "Volunteer Handbook")

Use this as a model for what good stories look like. It is not a template to copy: write stories from the user's own brief.

**The brief in one line:** a short handbook that welcomes new volunteers at a food pantry and tells them what to do on their first day. It produces a document only.

**Why the stories look like this:** the outline is approved before any drafting; "testing" is a checklist drawn from the brief plus a fresh-eyes read by someone who was not involved; every fact and phone number is checked against its source.

### Story 1 ★ STOP FOR REVIEW — Outline and audience

**Reads first:** `PROJECT_BRIEF.md`.

**Build:**
- One paragraph: who this is for and what they should be able to do after reading it.
- An outline with one line on each part: welcome, first-day checklist, safety rules, who to ask for what.
- Two or three short sample sentences showing the tone.

**Tests:** the owner reads the outline against the success definition in the brief and says what is missing or unneeded.

**Done when:** the owner has approved the outline.

**Prompt:**
```
Read the rules file and PROJECT_BRIEF.md. Write one paragraph on who the handbook is for and what they should be able to do afterwards, an outline with one line per part, and two or three sample sentences in the tone the brief describes. Do not draft the full handbook. Stop for review and ask the owner what is missing or unneeded.
```

### Story 2 — First draft

**Reads first:** the approved outline, `GUIDE-house-style.md`.

**Build:**
- A complete first draft of every part, in the agreed tone, with a visible mark ("CHECK:") on every fact, number and name that still needs confirming.

**Tests:** every "CHECK:" mark is listed with where its answer will come from; a read-through against the brief's checklist finds no part missing; sentences read aloud do not need a second try.

**Done when:** the draft is complete and the list of things to confirm is written.

**Prompt:**
```
Read the approved outline and GUIDE-house-style.md. Draft every part of the handbook in the agreed tone. Put CHECK: next to every fact, number, name or phone number you could not confirm from the brief, and list them at the end with where each answer should come from. Do not invent a fact to fill a gap. Log it and stop.
```

### Story 3 ★ STOP FOR REVIEW ⚠️ — Check the safety rules and contacts, then a fresh-eyes read

> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here): A wrong safety rule or phone number in a document people trust can cause real harm.

**Reads first:** the draft, the list of things to confirm, the county safety rules named in the brief.

**Build:**
- Every safety rule and contact checked against its source, with the source named beside it.
- A fresh-eyes read by someone who has never volunteered there, with their notes recorded.

**Tests:** no "CHECK:" mark remains without an answer from a named source; the fresh-eyes reader can say, without looking, where to go on day one and which three safety rules matter most.

**Done when:** the manager has signed off the safety rules and contacts in writing.

**Prompt:**
```
Read the draft, the list of things to confirm and the safety rules named in the brief. Check every safety rule and contact against its source and write the source next to it; leave a CHECK: on anything you cannot confirm. Do not soften or reword a rule without saying so. Then stop for review: give the manager the list of rules and contacts with sources, and ask for a written yes.
```
