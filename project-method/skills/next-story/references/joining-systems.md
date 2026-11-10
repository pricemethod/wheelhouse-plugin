# Joining two or more systems

When a project uses more than one outside system together (for example Wheelhouse for prices and occupancy, and a property management system for payouts and fees), most quiet mistakes happen where the two meet. Settle these four things early, with the owner, and write the answers in `GUIDE-reference.md` under "How the systems fit together".

## 1. Which record is the same thing in both

- Find how a property (or a reservation, an owner) in one system matches the same one in the other. Look for an ID that both hold: often the listing ID from the system the listings came from. If there is no shared ID, matching by name or address is a last resort, and the owner checks the matches.
- **Never assume the match. Prove it on real data:** take a handful of records the owner knows well and show them side by side from both systems. The owner confirms them before anything is built on the match.
- Decide what happens to a record found in only one system: skipped, flagged to the owner, or counted separately. Never dropped silently.
- Multi-unit properties may be one record in one system and several in the other. Check, and write down how they line up.

## 2. Which system is the source of truth for each fact

For every fact the project uses, name the one system it comes from (for example: nightly prices and occupancy from Wheelhouse; payouts, fees and owner splits from the property management system). When two systems disagree, the source of truth wins, and the difference is shown to the owner, not hidden.

## 3. Lining up the details

- **Dates:** check-in to check-out, or nights? Which time zone? A stay that crosses a month end is split the same way in both.
- **Money:** currency, cents or whole amounts, and whether taxes and fees are included.
- **Status:** what counts as a real booking in each (cancelled, pending, owner stays).

## 4. In the plan

- After each system's own read-only story, an early **matching story** (⚠️, because a wrong match spreads into every number) that builds the match, shows the owner the side-by-side sample, and writes the answers above into `GUIDE-reference.md`. It stops for the owner's review (★).
- Every later story that combines the systems reads that section first.
- A change written to either system follows that system's own rules (`references/wheelhouse.md` for Wheelhouse, `references/other-systems.md` for the rest), one system at a time, each with its own yes.
