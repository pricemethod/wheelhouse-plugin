# Safety — {{project_name}}

This project can change something real. This file is the short list of what must never happen and who must say yes first. It is read at the start of every story that touches the real thing, and it is only ever tightened, never loosened, without the owner ({{owner_name}}) writing the change here with the date.

## What must never happen
{{never_events}}

## What the project connects to
{{systems}}

## The rules
1. **Read-only and sandbox first.** Anything that changes real things is tried on a safe copy or test account before the real one. The safe copy is named here, and the real one stays read-only until the owner says otherwise in writing.
2. **One doorway in the code.** Every change goes through a single checked doorway that refuses anything not allowed. The screen hiding a button is for the person's convenience; the doorway is the actual protection.
3. **Never trust what the screen says.** The doorway looks up the target itself and does not accept the screen's word for what it is allowed to change.
4. **Read fresh, change only what was asked.** Read the current state right before a change and change only what was asked. If saving one item replaces a whole list, send back every other item exactly as it was.
5. **What was approved is what is sent.** If anything changed between the owner's approval and the moment of sending, send nothing and show the owner the new picture.
6. **Try it once first.** The first real action that cannot be undone is done for one real target only, checked, and only then done for the rest, with another yes.
7. **A fresh yes every time.** Each change to real things needs a fresh yes with the exact target and values in front of the owner. An earlier yes does not cover the next one.
8. **Read it back afterwards.** After a change, read the real thing again to confirm it says what it should and nothing else changed.
9. **Partial success is not success.** If part of a change worked and part did not, say exactly which, and show the owner before doing anything else.
10. **Check every part before doing any part.** When one action has several parts that cannot be undone together, check every part is still allowed before doing the first, and report each part separately.
11. **Undo plan, and put test changes back.** Before any real change, note how it would be undone; after testing on real things, put them back the way they were.
12. **Respect limits, retry politely.** Stay within the system's request limits; when told to slow down, wait and retry a few times, then report it.
13. **Secrets stay private.** Keys and logins live in a private file that is never shared or committed, are read only where needed, and are never printed in the chat, the log or on a screen.
14. **The least access that works.** Use read-only access wherever only reading is needed.
15. **History is only ever added to.** The log is never edited or shortened; a mistake in an old entry is corrected by a new one.

## Who must say yes to what
| Action | Who says yes | Where it is recorded |
|---|---|---|
| Changing anything on the safe copy | {{owner_name}} (once per story) | the log entry |
| Changing anything real | {{owner_name}} (each time) | the log entry, with exact target and values |
| Deleting anything | {{owner_name}} (each time) | the log entry |

## What went wrong before
*(Add each incident or near miss, with the date and the new rule it produced.)*
