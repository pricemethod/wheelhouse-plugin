# Testing layers: software

How to check software work, layer by layer, cheapest first. The short version lives in the project's rules file ("How we check software work"); this page explains each layer, gives an example, and says how much a project of each size needs. Use it when writing a story's **Tests** (with `story-writer`) and when checking a story (with `next-story`).

## How much each size needs

| Layer | Lite | Standard | Full |
|---|:-:|:-:|:-:|
| Logic checks | when there is a rule or calculation | ✓ | ✓ |
| Output checks | ✓ (by eye is fine) | ✓ | ✓ |
| Rule-enforcing checks | — | when a house rule keeps being broken | ✓ |
| Break it on purpose | ✓ | ✓ | ✓ |
| Pinned real sample | — | when numbers matter | ✓ |
| Compare with an independent source | — | when numbers or real data matter | ✓ |
| Try it for real | ✓ | ✓ | ✓, on a real phone too |
| Before the log entry | ✓ | ✓ | ✓ |

"Break it on purpose", "Try it for real" and "Before the log entry" apply to every project, however small.

## The layers

### Logic checks
**What:** small automatic tests of the rules and calculations: totals, dates, who can see what, what happens with nothing in the list.
**When:** as soon as there is a rule that could be wrong without anyone noticing.
**Example (an invented tool-lending site):** "a tool already lent for Saturday cannot be lent again for Saturday"; "a request for last week is refused".
**Break it:** change the rule to allow double lending and confirm the check fails.

### Output checks
**What:** checks of what the person actually sees: labels, numbers, messages, the order of things, what a screen says when it is empty or something went wrong.
**When:** every screen or file a person reads.
**Example:** the borrow page shows the tool's name, the owner's first name only, and the dates; with no tools listed it says "No tools yet" and what to do.
**Break it:** remove the empty message and confirm the check notices.

### Rule-enforcing checks
**What:** checks that read the project itself and fail when a house rule is broken: a one-off piece where a shared one must be used, a color that is not in the agreed list, a private file referenced from the wrong place.
**When:** once a rule matters enough that forgetting it would cost something, or it has already been forgotten once.
**Example:** "every screen uses the shared empty-state piece; nobody writes their own 'nothing here' paragraph".
**Break it:** add a hand-written one and confirm the check fails.

### Break it on purpose
**What:** after writing any new check, deliberately break the thing it protects, confirm the check fails, then put it back. A check that cannot fail proves nothing.
**When:** every new check, every time. Record it in the log ("broke the double-lending rule; the check failed; restored").
**Why it matters:** checks often pass for the wrong reason (they test nothing, or the wrong thing). This is the only way to know.
**Tip:** if breaking something does *not* make a check fail, that is a finding: tighten the check, then break it again.

### Pinned real sample
**What:** a small, real example with the right answer worked out by hand, saved with the project and checked every time.
**When:** wherever numbers or a real data shape matter, especially when the real source behaves differently from its own documentation.
**Example:** one real month of bookings for one item, with the total worked out on paper, kept as a file; the check must reproduce it exactly.
**Break it:** change one number in the sample and confirm the check fails.

### Compare with an independent source
**What:** get the same fact a second, separate way and compare, instead of only checking that the project agrees with itself.
**When:** before trusting any number people will act on, and after connecting to real data.
**Example:** the site's "tools lent this month" matches a count made directly from the raw records; a calendar's marks match a separate read of the same source, night by night.
**Break it:** change one record in the copy and confirm the comparison reports the difference.
**Rule:** a difference you cannot explain is not a match.

### Try it for real
**What:** run it and use it the way a real person would: click through it, at phone width and desktop width, with real-looking data, and on a real phone before calling a touch or layout story finished.
**When:** every story that changes something a person sees or does.
**Gotchas worth knowing:**
- A phone or browser tab that has been open for a while can keep an **old copy** of the styles or scripts. After changes, fully reload or reopen the page before judging it.
- Something that looks right on a computer can be too small to tap on a phone. Every button should be about the size of a fingertip.
- Check the empty, loading and trouble states, not only the happy path.

### Before the log entry
**What:** run the whole set of checks, note anything odd even if it did not block you, and write down what you actually did, including what you did not check.
**When:** at the end of every story.

## Edge cases to try in most software
- Nothing at all (an empty list, a new account), exactly one, and a lot.
- The first and last day of a month and of a year; a range that crosses either.
- Time zones and clocks: "today" for the person can differ from "today" for the computer.
- Rounding of money and percentages; very large and very small numbers.
- Duplicates, missing values, and a record that was deleted elsewhere.
- Identifiers that are not what they look like: never assume a number starts at 1, has no gaps, or is in order.
- Two people doing the same thing at once; the same button pressed twice.
- A slow or failed connection: what does the person see?
