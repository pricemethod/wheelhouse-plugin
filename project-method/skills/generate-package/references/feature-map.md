# The feature map (`FEATURE_MAP.md`)

Software projects on a Standard or Full plan get a feature map: what the project has **now**, feature by feature. The build log is the history (how we got here); the map is the current state (what is here now). It lets a later session, or a new person taking the project over, find any feature, see what it depends on, and see which steps made it what it is, without reading the whole log.

## The shape of an entry

Each feature is a `###` heading under `## Features`, with these lines in this order:

```markdown
### Owner statements
- **What it does:** Works out each owner's monthly figures and shows one statement per owner.
- **Where it lives:** `app/statements.py`, `app/templates/statement.html`
- **Depends on:** Booking export (outside: the monthly spreadsheet) · Owner list
- **Built and changed by:** Story 1.1 (first look) · Story 2.1 (real figures) · F1.2 (added cleaning fees)
- **Watch out:** cleaning fees are per stay, not per night.
```

- **What it does:** one plain sentence, in the owner's words where possible.
- **Where it lives:** the files or folders, each in backticks, as paths from the project folder. Only paths that exist.
- **Depends on:** other features in this map (by their heading), and anything outside the project marked "(outside: …)", such as a service, an account or a spreadsheet. "Nothing" if it stands alone.
- **Built and changed by:** every step that built or changed it, oldest first, each with a few words on what it did.
- **Watch out:** optional; anything that would surprise the next person (the same kind of thing as the rules file's "Gotchas").

A "feature" is something the owner would recognise and name ("the statement preview", "the email safety check"), not a file. Several files make one feature; a shared piece that several features use (for example "Owner list") can be its own entry that the others depend on.

## Keeping it current (`next-story`)

At the end of every step, before writing the log entry:
- **A step that builds a new feature** adds an entry.
- **A step that changes a feature** updates its lines (where it lives, what it depends on) and adds itself to "Built and changed by".
- **A step that built nothing in the project** (answering the open questions, a check that changed nothing) adds one line under `## Steps that changed no feature`: `- Story 0.2: answered the open questions`.
- **When a feature is removed or replaced,** delete its entry (the log keeps the history) and say so in the log entry.
- Replace each placeholder line in italics the first time its section gets a real line.

Then check it. If you can run Python: `python3 -I <plugin folder>/scripts/check_package.py <project folder> --map-only`. It checks every entry has its four lines, every path under "Where it lives" exists, and every step the log calls complete is listed somewhere in the map. If you cannot run it, check those three things by eye.

The map is the one package file Claude rewrites in place (unlike the log and the feature plan, which only grow), because it describes the present.

## Using it to plan (`add-feature`)

Before writing a new feature, read the map. Use it to fill "what already exists" in the feature section, and say which existing features the new one builds on or changes. A story that changes an existing feature names that feature's files under **Reads first**.
