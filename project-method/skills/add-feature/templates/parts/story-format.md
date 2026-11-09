### Story X.X — <short name>
<!-- note: if the story ends at a review gate, the heading is `### Story 1.2 ★ STOP FOR REVIEW — <name>`; if it needs extra care, add ⚠️ after the number too: `### Story 1.2 ⚠️ — <name>`. -->

<!-- note: include the next line only for a ⚠️ story, with the reason in one sentence on the same line (changing real data, money, numbers people will act on, anything hard to undo). -->
> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here): <one sentence: why a quiet mistake here would be costly>

**Reads first:** the files and sections this story needs, and nothing else.

**Build:**
- What to make, as a short list of concrete outcomes (not steps to follow blindly).

**Tests:** how we will know it works: the checks to run, and at least one that is deliberately broken to prove the check can fail.

**Done when:** the observable result that means this story is finished.

**Prompt:**
```
Read the rules file and the last few log entries, then this story. <Instruction in plain words: what to make, what to avoid, what to check.> Run the checks above, check it yourself as a user would, write the log entry, and stop at any review gate.
```
