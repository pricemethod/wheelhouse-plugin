# Wheelhouse stories

Early stories the Wheelhouse pack adds to a plan. Adapt each to the project (its numbering, its files, what it needs from Wheelhouse) but keep the shape, the marks and the checks. `generate-package` places them; `add-feature` uses them when a feature brings Wheelhouse in.

| Story | Add it when | Where it goes |
|---|---|---|
| A. Look at the Wheelhouse data | Always | First story that touches Wheelhouse, right after Story 0.2 (or after the first look on made-up data, for software) |
| B. Set up the API key | The project is software that runs without Claude (a website, app or script), not only through Claude's connector | Before the first story that calls the API |
| C. The checked doorway for Wheelhouse changes | The project changes anything in Wheelhouse | After the reading stories, before any change |
| D. The first real change, on one listing | The project changes anything in Wheelhouse | Straight after C, never inside a bigger story |
| E. The team page and its refresh | The project is a page a team uses, refreshed by Claude (guide §2) | After A, as the first story that builds the page |

When the project also uses other systems, the matching story from `references/joining-systems.md` comes after A and after each other system's own read-only story.

---

### Story A ★ STOP FOR REVIEW — Look at the Wheelhouse data

**Reads first:** `CLAUDE.md`; `GUIDE-reference.md` (Wheelhouse); the Wheelhouse pack's guide, sections 1, 3 and 4.

**Build:**
- Read, and only read, the Wheelhouse data the project needs, for a few listings the owner names: through the connector, or the API with the key from Story B.
- Write into `GUIDE-reference.md` under "Wheelhouse": each endpoint or tool used, the fields the project needs and what they really hold (with a short sample, personal details left out), multi-unit listings if any, currencies, and anything that differs from the guide (also a dated line under "Gotchas" in `CLAUDE.md`).
- Nothing is changed in Wheelhouse.

**Tests:** the sample matches what the owner sees in Wheelhouse for the same listing and dates (the owner checks at least one number); a deliberately wrong listing ID gives the expected error, not an empty success.

**Done when:** the owner has seen the sample, confirmed a number against Wheelhouse, and said the fields are the ones the project needs.

**Prompt:**
```
Read the rules file and the last few log entries, then this story and the Wheelhouse pack's guide sections 1, 3 and 4. Read (never change) the Wheelhouse data this project needs for the few listings the owner names. Write what you found into GUIDE-reference.md under "Wheelhouse", with a short sample that leaves out guest names and contact details, and note anything that differs from the guide under "Gotchas" in CLAUDE.md. Check one number with the owner against Wheelhouse itself. Run the checks above, write the log entry, and stop for the owner's review.
```

### Story B — Set up the API key

**Reads first:** `CLAUDE.md`; the Wheelhouse pack's guide, section 2.

**Build:**
- A private place for the key in the project (a file the rules list as never shared, never saved to history), and code that reads it from there and nowhere else.
- Plain steps for the owner: where to make the key in Wheelhouse (Account → API Key), read-only if the project only reads, and where to put it. The owner puts it there; it is never pasted into the chat.
- One read-only call that proves the key works, reporting only "works" or the error, never the key.

**Tests:** the proving call succeeds; with the key file missing, the project stops with a plain message instead of crashing or sending an empty key; the key does not appear in the log, any saved file or anything printed.

**Done when:** the owner has put the key in place and the proving call says it works.

**Prompt:**
```
Read the rules file and the last few log entries, then this story and the Wheelhouse pack's guide section 2. Set up a private place for the Wheelhouse API key and code that reads it only from there. Give the owner plain steps to make the key (read-only if the project only reads) and put it there themselves; never ask them to paste it in the chat, and never print it. Prove it works with one read-only call. Run the checks above and write the log entry.
```

### Story C ⚠️ — The checked doorway for Wheelhouse changes

> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here): every change to the owner's real prices and settings will go through this, so a mistake here reaches real bookings.

**Reads first:** `CLAUDE.md`; `SAFETY.md`; the Wheelhouse pack's guide, sections 5, 6 and 7; `references/wheelhouse.md`.

**Build:**
- One function every Wheelhouse change goes through. It refuses a listing the owner hasn't allowed; fetches the current state immediately before; for a settings change, keeps every existing rule and sends each list whole; for a custom rate, works out which existing rates it trims, splits or replaces, and the combined value with the right formula for the type; shows the owner the exact before and after; and after the change, reads the `warnings`, any partial result, and the listing back.
- Tried only on made-up data shaped like the real replies. Nothing is sent to Wheelhouse in this story.

**Tests:** a change to a listing not allowed is refused before anything is sent; a settings change built from only the new rule is caught (the other rules would be lost); both combine formulas pinned by tests that name the direction (adjustment adds points, fixed multiplies the price), and swapping them makes a test fail; a reply with a warning is reported as "not fully applied", never as success.

**Done when:** all the tests pass on made-up data, and the owner has read, in plain words, what the doorway will check before every change.

**Prompt:**
```
Read the rules file, SAFETY.md and the last few log entries, then this story, references/wheelhouse.md and the Wheelhouse pack's guide sections 5–7. Build the one function every Wheelhouse change goes through, exactly as the Build list says, and try it only on made-up data: send nothing to Wheelhouse. Include the deliberately failing checks. Explain to the owner in plain words what it checks before every change, run the checks above, write the log entry, and stop.
```

### Story D ★ STOP FOR REVIEW ⚠️ — The first real change, on one listing

> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here): this is the first time the project changes the owner's real Wheelhouse account.

**Reads first:** `CLAUDE.md`; `SAFETY.md`; `references/before-outward-actions.md`; the Wheelhouse pack's guide, sections 6 and 7.

**Build:**
- One change, to one listing (a test listing if the account has one, otherwise one the owner chooses), through the doorway from Story C, after showing the owner the exact listing, dates, values and what it replaces, and getting a fresh yes to that exact change.
- Afterwards: the reply's warnings, the listing read back, and what changed (and anything that didn't) told to the owner in plain words. How to undo it, written in the log.

**Tests:** the read-back matches what was sent; any warning is shown; nothing else on the listing changed (compare before and after).

**Done when:** the owner has seen the change in Wheelhouse itself and said it is right. Wider changes come only after that, each with its own yes.

**Prompt:**
```
Read the rules file, SAFETY.md and the last few log entries, then this story, references/before-outward-actions.md and the Wheelhouse pack's guide sections 6 and 7. Go through before-outward-actions line by line. Show the owner the exact change (listing, dates, values, what it replaces) and wait for a fresh yes to that exact change. Make it through the checked doorway, for this one listing only, then read the warnings and the listing back, and tell the owner exactly what changed and anything that didn't. Write the log entry, including how to undo it, and stop for the owner's review.
```

### Story E ★ STOP FOR REVIEW — The team page and its refresh

**Reads first:** `CLAUDE.md`; `GUIDE-reference.md` (Wheelhouse); the Wheelhouse pack's guide, section 2; `references/wheelhouse.md` (rule 7).

**Build:**
- The page (a Claude artifact) showing the saved copy of the data the project needs, with the tools the brief asks for (search, sort, filters, flags). The page reads only its own saved copy and never connects to Wheelhouse.
- Its storage set so everyone it is shared with can read the copy and only the owner (and editors) can replace it.
- The refresh: Claude reads the data through the owner's Wheelhouse connector (read only) and saves it into the page with the time it was saved. Write the exact words that ask for it ("refresh my … page") in `CLAUDE.md` and on the page itself, where only the owner sees them.
- The page says when the copy was saved, and what it shows before the first refresh and if the copy can't be loaded.

**Tests:** the saved copy matches what the owner sees in Wheelhouse for at least one listing; someone the page is shared with as a viewer can read it but can't replace it (check with viewer-level access); a refresh shows the new saved time on a page that is already open; the page contains no connector access (its declared abilities list none).

**Done when:** the owner has shared it with one teammate, the teammate has used it without connecting Wheelhouse, and the owner has seen a refresh arrive.

**Prompt:**
```
Read the rules file and the last few log entries, then this story, the Wheelhouse pack's guide section 2 and rule 7 in references/wheelhouse.md. Build the team page as a Claude artifact that shows only its saved copy and never connects to Wheelhouse itself. Set its storage so everyone can read the copy and only the owner and editors can replace it. Then do the first refresh: read the data through the owner's Wheelhouse connector, read only, and save it into the page with the time. Write the words that ask for a refresh in CLAUDE.md. Run the checks above, write the log entry, and stop for the owner's review.
```
