# Safety patterns

For any project that can change something real: send email or messages, publish or post, delete, pay or charge, or update data that someone else relies on. These patterns turn the rules in a project's `SAFETY.md` into things you can build and check. Each says what to do, why, how to check it, and how much a project of each size needs. Use them when writing stories (`story-writer`), when building them (`next-story`), and together with `references/before-outward-actions.md`.

## How much each size needs

A project that can change something real is never Lite. For **Standard**, every pattern below marked ✓ is required; for **Full**, all of them are, and each connected system gets its own section in the reference guide.

| Pattern | Standard | Full |
|---|:-:|:-:|
| 1. Read-only and sandbox first | ✓ | ✓ |
| 2. One doorway in the code | ✓ | ✓ |
| 3. Never trust what the screen says | ✓ | ✓ |
| 4. Read fresh, change only what was asked | ✓ | ✓ |
| 5. What was approved is what is sent | when the change is reviewed before sending | ✓ |
| 6. Try it once first | ✓ | ✓ |
| 7. A fresh yes every time | ✓ | ✓ |
| 8. Read it back afterwards | ✓ | ✓ |
| 9. Partial success is not success | ✓ | ✓ |
| 10. Check every part before doing any part | when one action has two or more parts | ✓ |
| 11. Undo plan, and put test changes back | ✓ | ✓ |
| 12. Respect limits, retry politely | when the system has limits | ✓ |
| 13. Secrets stay private | ✓ | ✓ |
| 14. The least access that works | when the system offers it | ✓ |
| 15. History is only ever added to | ✓ | ✓ |

## The patterns

### 1. Read-only and sandbox first
**Do:** start read-only. Every change is tried on a safe copy (a test account, a test inbox, a copy of the list) before the real thing. Name the safe copy in `SAFETY.md`; the real thing stays read-only until the owner says otherwise in writing.
**Check:** while testing, the doorway (pattern 2) refuses anything that is not the safe copy; prove it by trying a real target on purpose and watching it be refused.

### 2. One doorway in the code
**Do:** every change to anything real goes through one checked place that refuses anything not allowed. Hiding a button on the screen is a convenience; the doorway is the protection.
**Check:** search the project for any other way to make the change (there must be none); break the doorway's refusal on purpose and confirm the check fails.

### 3. Never trust what the screen says
**Do:** the doorway looks up the target itself (who it is, whether it may be changed) instead of accepting the screen's word for it. Anything sent from a screen can be wrong or tampered with.
**Check:** send the doorway a request that claims to be allowed but is not; it must refuse.

### 4. Read fresh, change only what was asked
**Do:** read the current state right before a change, not from earlier. Change only what was asked and carry everything else forward unchanged. Some systems replace a **whole list** when you save one item: read the whole list fresh, change the one item, and send back every other item exactly as it was, or the others are deleted.
**Check:** a test where the list has several items, one is changed, and all the others are still there afterwards.

### 5. What was approved is what is sent
**Do:** when a change is shown to the owner for approval, remember exactly what was shown. Just before sending, read the current state again; if it differs from what was approved, send nothing and show the owner the new picture.
**Check:** change the state between approval and sending in a test; nothing is sent and the owner is told.

### 6. Try it once first
**Do:** the first time an action that cannot be undone is done for real, do it for one real target only, with the owner's yes, check it worked, and only then do the rest, with another yes. It is its own story.
**Check:** the first real action reaches exactly one target, and the log records which.

### 7. A fresh yes every time
**Do:** every real change needs the owner's yes to that exact change, with the target and values in front of them. An earlier yes does not cover a later change.
**Check:** the log shows a yes for each real change, in the owner's words, with what it covered.

### 8. Read it back afterwards
**Do:** after a change, read the real thing again and confirm it now says what it should, and that nothing else changed.
**Check:** the story's tests include the read-back; the log says what it showed.

### 9. Partial success is not success
**Do:** if part of a change worked and part did not, say exactly which part, show the owner, and stop. Never report "done" for a half-finished change, and never treat a bare "OK" from a system as proof: look for warnings or partial results in its reply.
**Check:** a test where one of several changes fails; the report names it.

### 10. Check every part before doing any part
**Do:** when one action has several parts with no way to undo them together (say, an email and a record update), check that every part is still allowed and still matches what was approved **before** doing the first. Then report each part's outcome separately.
**Check:** make the second part's check fail in a test; the first part must not have been done.

### 11. Undo plan, and put test changes back
**Do:** before a real change, write how it would be undone (or say plainly that it cannot be). After testing on real things, put them back exactly as they were, and record that in the log.
**Check:** the log for each real test shows what was changed and how it was put back.

### 12. Respect limits, retry politely
**Do:** stay within a system's request limits (for example, a number of requests per minute shared by everything using the same account). When the system says "slow down", wait as long as it asks before trying again; give up after a few tries and report it.
**Check:** a test where the system says "slow down"; the project waits and retries instead of hammering it.

### 13. Secrets stay private
**Do:** keys, passwords and tokens live in one private file that is never shared or committed, are read only by the part of the project that needs them, and are never printed in the chat, the log, a screen or an error message. Never ask the owner to paste one into the chat.
**Check:** search the project and the log for the secret's first few characters; there must be no match outside the private file. Confirm the private file is excluded from snapshots.

### 14. The least access that works
**Do:** where a system offers read-only access, use it for everything that only reads, and keep write access to the few places that need it.
**Check:** the read-only parts work with a read-only key.

### 15. History is only ever added to
**Do:** the log and the feature plan are only ever added to; nothing earlier is edited or deleted. If a past entry was wrong, a new entry says so.
**Check:** the plugin's `scripts/append_only.py` proves an edit only added text (`--log` for the log, `--feature-plan` for the feature plan).
