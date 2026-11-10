# Testing layers: data and analysis

How to check data and analysis work, layer by layer. The short version lives in the project's rules file; this page explains each layer, gives an example, and says how much a project of each size needs. Use it when writing a story's **Tests** and when checking a story.

## How much each size needs

| Layer | Lite | Standard | Full |
|---|:-:|:-:|:-:|
| Definitions first | ✓ | ✓ | ✓ |
| Read-only by default | ✓ | ✓ | ✓ |
| Small pinned sample | ✓ | ✓ | ✓ |
| Compare with an independent source | when a number will be acted on | ✓ | ✓, for every published figure |
| Break it on purpose | ✓ | ✓ | ✓ |
| Edge cases | the obvious ones | ✓ | ✓ |
| Say what was and was not checked | ✓ | ✓ | ✓ |

## The layers

### Definitions first
**What:** every measure written down in plain words before any number exists: what is counted, over what period, what is left out, and how ties and missing values are treated. The owner approves them.
**Why:** most wrong numbers are right answers to the wrong question. Two people can mean different things by "occupancy" or "a visit".
**Example (an invented library analysis):** "A visit is one person passing the door counter. Closed days are left out, not counted as zero. A typical day is the median of open days."
**Break it:** ask "what if a branch counts twice at a side door?" If the definition has no answer, it is not finished.

### Read-only by default
**What:** the work reads from its sources and never changes them. Work on a copy if anything has to be cleaned.
**Why:** the source is someone else's record; changing it, even by accident, is the costliest mistake in data work.
**How to check:** the source file's date and size are the same after the work as before.

### Small pinned sample
**What:** a small, real slice of the data with the answer worked out by hand, kept with the project, and reproduced exactly every time.
**Example:** one branch, one week, visits added up on paper by hour; the analysis must match to the last visit.
**Break it:** change one value in the sample and confirm the check fails.

### Compare with an independent source
**What:** get the same figure a second way (the source's own report, a manual count, a different method, last year's published figure) and reconcile every difference.
**Example:** the monthly totals match each branch's own monthly report; where they do not, each gap is explained (a closure, a counter fault).
**Rule:** a match you cannot explain is not a match. Write the explanation next to the figure.
**Tip:** when a published system produces its own version of the number, reproduce that number exactly first, using its definitions; then any difference in your own view is a choice you can explain.

### Break it on purpose
**What:** change an input or a rule on purpose and confirm the result changes the way you expect, and that the checks notice.
**Example:** count one record twice; drop one month; shift a date by a day across a month end. Each should show up.

### Edge cases
**What:** the awkward cases to try every time: empty periods; a single record; missing values; duplicates; the first and last day of a range; a range that crosses a month or year end; leap days; time zones (a timestamp late at night can belong to a different day); a period with too little data to say anything (say so instead of showing a number).

### Say what was and was not checked
**What:** next to every result handed over, a short note: how it was checked, against what, and what the data cannot tell us.
**Example:** "Checked against each branch's monthly report (all match except March 2024, when one counter was broken for six days). This shows visits, not who visited or why."
