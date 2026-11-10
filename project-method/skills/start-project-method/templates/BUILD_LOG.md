# Build log — {{project_name}}

This is the memory between sessions. After every working session Claude adds an entry here. **Entries are only ever added, never edited or deleted.** If this log and the plan disagree, the log wins, and the entry says so.

## Entry format

<!-- include: parts/log-format.md -->

---

## [{{today}}] Project package created
<!-- note: write this entry LAST, after the package check has run, so "Checked how" states the real result. -->
**Status:** complete
**Files added:** {{package_files}}
**Files changed:** none
**What changed:** the project package for "{{project_name}}" was generated from the confirmed brief ({{project_type}}, {{size}} size).
**Checked how:** {{package_check}}
**Deviations from the plan:** none yet.
**Plan updates needed:** none.
**Open questions / follow-ups:** the open questions in PROJECT_BRIEF.md are scheduled as early stories in PLAN.md. Start with "What's next?".
