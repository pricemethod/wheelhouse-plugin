# Plan — {{project_name}}

{{one_liner}}

This plan breaks the project into small **stories**. Each story is sized to be finished and checked in one working session, and has a ready-to-use prompt. The rules for every session are in `CLAUDE.md`; what has actually happened is in `BUILD_LOG.md`. **If the log and this plan disagree, the log wins.**

## 1. How this plan works
- Work happens one story at a time, in order, unless the owner ({{owner_name}}) says otherwise.
- Each story lists what to read first, so nothing is built from memory.
- A story marked **★ STOP FOR REVIEW** ends with a summary and a way to look at the result; nothing further is built until the owner answers.
- A story marked **⚠️** needs extra care: a quiet mistake there would be costly, so it gets extra checks (and a stronger model or more thinking time helps).
- Every story ends with a log entry. Claude never changes this plan on its own: it proposes the exact change under "Plan updates needed", and makes it only after the owner says yes to that change.

## 2. Decisions and open questions
Everything decided so far, and everything still to be answered. Answers are added here as they are made, with the date (by Claude, with the owner's yes).

| # | Decision or question | Answer | Date |
|---|---|---|---|
| 1 | What is in scope | {{in_scope}} | {{today}} |
| 2 | What is deliberately out of scope | {{out_of_scope}} | {{today}} |
| 3 | Parked for later | {{later_ideas}} | {{today}} |
| 4 | How it is used and kept up to date | {{shape}} Why: {{shape_reason}} Check again if: {{shape_switch_if}} | {{today}} |
| 5 | Open questions from the brief (listed below) | answered in Story 0.2, or in its own story where the plan gives it one | |

**Open questions from the brief:**

{{open_items}}

## 3. {{phases_heading}}
<!-- note: phases_heading is rendered as "Phases" for Standard and Full, and "Order of work" for Lite; see the manifest. -->
<!-- if: size=standard,full; type=software -->
- **Phase 0, Foundations:** set up the project, how to run it and check it, and the safety rules.
- **Phase 1, A first version on made-up data:** the main screens or features working end to end against believable fake data, so the idea can be judged before real data is involved.
- **Phase 2, The real features:** each feature in the scope, built and checked one story at a time.
- **Phase 3, Real data and connections:** replace the fake data with the real thing, read-only first, in its own stories.
- **Phase 4, Bring it together and check it:** the full walk-through, the empty and error states, the phone and desktop check, and the final review.
<!-- /if -->
<!-- if: size=standard,full; type=data-analysis -->
- **Phase 0, The question and the definitions:** write down exactly what is being asked and how every measure is defined, before any number exists.
- **Phase 1, Sources and access:** get read-only access to each source and check early that it holds what we think it holds.
- **Phase 2, Build and validate:** produce the figures, then prove them against a hand-worked sample and an independent source.
- **Phase 3, Results and review:** present the results with what was and was not checked, and review them with the owner.
- **Phase 4, Hand-off:** package the results, the method and the caveats so someone else can use or repeat them.
<!-- /if -->
<!-- if: size=standard,full; type=other -->
- **Phase 0, Outline and audience:** who it is for, what they need, and the shape of the thing, agreed before drafting.
- **Phase 1, First draft:** a complete draft, kept honest about gaps.
- **Phase 2, Review rounds:** named reviewers, dated rounds, every requested change made or declined in writing.
- **Phase 3, Finish and hand over:** final checks where it will actually be seen, and delivery.
<!-- /if -->
<!-- if: size=lite -->
Lite plans have no phases. Work through the stories in order; the project is small enough that eight stories or fewer cover it. If the list grows past eight, say so and the plan is upgraded to Standard.
<!-- /if -->

## 4. Every story has this shape

<!-- include: parts/story-format.md -->

## 5. Stories

<!-- note: the generator replaces everything below with the project's real stories, written from the brief, keeping the two stories below as the first two. -->

<!-- if: type=software -->
### Story 0.1 ★ STOP FOR REVIEW — Choose how it is built and run, then set it up
**Reads first:** `CLAUDE.md`, `PROJECT_BRIEF.md`.
**Build:**
- A plain-words proposal for the owner: the simplest way to build this, where it will run (on this computer only, or online for people's phones), what it costs, and what the owner would need to do. The owner chooses.
- The starting files for the chosen way, kept as simple as the brief allows, a way to run it on this computer, and a way to run its checks.
- The exact commands written into the checking section of `CLAUDE.md`.
**Tests:** the checks run and pass on the empty project; break one on purpose and confirm it fails, then restore it.
**Done when:** the owner has chosen the approach, and a new session can run the project and its checks using only `CLAUDE.md`.
**Prompt:**
```
Read CLAUDE.md and PROJECT_BRIEF.md. In plain words, propose the simplest way to build this, where it would run, what it costs and what the owner would need to do, and wait for the owner to choose. Then set up the starting project for that choice, a way to run it here, and a way to run its checks, and write the exact commands into the checking section of CLAUDE.md. Run the checks, break one on purpose to prove it can fail, restore it, write the log entry, and stop for review.
```
<!-- /if -->
<!-- if: type=data-analysis -->
### Story 0.1 ★ STOP FOR REVIEW — Write down the question and the definitions
**Reads first:** `CLAUDE.md`, `PROJECT_BRIEF.md`.
**Build:**
- The exact question, in one sentence, and who will act on the answer.
- A plain-words definition of every measure: what is counted, over what period, what is left out.
- The list of sources the answer will come from and what each is trusted for.
- All of this written in a new file, `DEFINITIONS.md`, that later stories read.
**Tests:** the owner reads the definitions and confirms each means what they meant; any word with two possible meanings is split into two measures; try one awkward "what if" case (a record counted twice, a missing day) against each definition, and if a definition has no answer, it is not finished.
**Done when:** the owner has signed off the definitions in writing.
**Prompt:**
```
Read CLAUDE.md and PROJECT_BRIEF.md. Write the exact question, a plain-words definition of every measure the answer needs (what is counted, over what period, what is left out), and the list of sources, in a new file DEFINITIONS.md. Test each definition against an awkward "what if" case. Do not produce any numbers yet. Write the log entry after the owner answers, then stop for review and ask the owner to confirm each definition.
```
<!-- /if -->
<!-- if: type=other -->
### Story 0.1 ★ STOP FOR REVIEW — Outline and audience
**Reads first:** `CLAUDE.md`, `PROJECT_BRIEF.md`.
**Build:**
- A one-paragraph statement of who this is for and what they should be able to do afterwards.
- An outline of the whole piece or process, with one line on each part.
- The format and tone, in a few examples.
- All of this in a new file, `OUTLINE.md`, that later stories read.
**Tests:** the owner reads the outline against the success definition in the brief and says what is missing or unneeded; take one part out on purpose and check the brief's checklist notices the gap, then put it back.
**Done when:** the owner has approved the outline.
**Prompt:**
```
Read CLAUDE.md and PROJECT_BRIEF.md. In a new file OUTLINE.md, write a one-paragraph statement of the audience and what they should be able to do afterwards, a full outline with one line per part, and the format and tone with two or three short examples. Check the outline against the brief's success sentence. Do not draft the full piece yet. Stop for review, ask the owner what is missing or unneeded, and write the log entry once they answer.
```
<!-- /if -->

### Story 0.2 — Answer the open questions
**Reads first:** `PROJECT_BRIEF.md` (the open questions), this plan's decisions table.
**Build:**
- For each open question, the quickest way to find out the real answer (ask a person, look at the real source, try a small experiment), and the answer.
- Each answer added to the decisions table (with the owner's yes), and any new story it creates proposed as a plan change.
**Tests:** every open question is either answered with evidence or explicitly moved to "later" by the owner; for each answer, say what evidence would have changed it.
**Done when:** the decisions table has no open question that blocks the next part of the work.
**Prompt:**
```
Read PROJECT_BRIEF.md and the decisions table in PLAN.md. For each open question, find the real answer the quickest honest way and record the evidence in the log. Propose the exact decisions-table rows under "Plan updates needed" and add them once the owner says yes. Do not guess an answer you cannot back up; say it is still open. Write the log entry and stop.
```

## 6. How we check the work (summary)
The full checking approach for this kind of project is in `CLAUDE.md`. In short: every story names its checks, each new check is broken on purpose once to prove it can fail, the result is used the way a real person would use it, and the log entry says exactly what was and was not checked.

## 7. Later ideas
{{later_ideas}}

New ideas go here first. When one is ready to build, it gets its own section with stories (see `FEATURE_PLAN.md` once it exists), written after a review, never squeezed into the stories above.
