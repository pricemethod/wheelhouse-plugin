# Scope: what the project connects to, and what that switches on

The method is the same for every project. What changes is the extra knowledge Claude brings, and that depends on one thing: **which outside systems the project uses**. The interview finds out (Q-CONNECT-1), the brief records it, and every later skill reads it from the brief. The person never picks a "mode".

## The three scopes

| Scope | When | What switches on |
|---|---|---|
| **Own project** | No Wheelhouse data. It may use nothing outside, or other systems (a spreadsheet, an email service, a booking system). | The core method. For each outside system: `references/other-systems.md`. |
| **Wheelhouse** | It reads or changes the person's Wheelhouse data, and nothing else outside. | The core method plus the Wheelhouse pack: `packs/wheelhouse/README.md`. |
| **Wheelhouse plus other systems** | Wheelhouse data together with at least one other system (for example a property management system for payouts and fees). | The core method, the Wheelhouse pack (`packs/wheelhouse/README.md`), `references/other-systems.md` for each other system, and `references/joining-systems.md`. |

A file the owner hands over once (a spreadsheet export) is a data source, not a system; it does not change the scope. A system the project talks to while it runs does.

## Recording it

Write each system on the brief's **Systems and accounts** line with what it is used for and which guide covers it, separated by semicolons, then the scope in brackets at the end:

> Wheelhouse (prices, occupancy; Wheelhouse pack); Guesty (payouts and fees; other-systems guide) [scope: Wheelhouse plus other systems]

> None [scope: own project]

If a system is known only by kind ("whatever sends the texts"), write the kind with "(not chosen yet)"; the other-systems guide applies once it is chosen.

## Saying it to the person

Once, in plain words, when the scope is first clear, and again only if it changes. Never use the word "scope" or "pack" with them.

- Own project with no systems: say nothing extra.
- Own project with a system: *"Since this connects to Guesty, I'll look at its own instructions first and only read from it until we've checked what it holds."*
- Wheelhouse: *"Since this uses your Wheelhouse data, I'll follow Wheelhouse's own rules for it: look before changing anything, and ask you before every change."*
- Wheelhouse plus others: the Wheelhouse sentence, then *"I'll also check early on that the same property lines up in both, before we build on it."*

## When it changes

The scope can change at any stage. A feature that brings in a new system (`add-feature`) records it in the feature section, switches on what the table above says from then on, and gets that system's early read-only story (and the matching story, if it is now Wheelhouse plus others). The brief stays as confirmed; the change is written in the feature section and the log.

## Every skill reads the same line

`start-project-method` writes it. `generate-package` uses it to choose the guides, rules and early stories. `next-story` reads it before any step that touches a system. `add-feature` reads it and updates it through the feature section. `where-are-we` mentions it in one line when it reports.
