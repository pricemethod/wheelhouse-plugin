# Wheelhouse pack

Switches on when the brief's systems include Wheelhouse (see `references/scope.md`): the project reads or changes anything in the person's Wheelhouse account (listings, prices, occupancy and other numbers, reservations, custom rates, minimum stays, other settings), through the Wheelhouse connector in Claude or the Wheelhouse RM API.

## What it adds

| File | Read it when |
|---|---|
| `references/wheelhouse.md` (in the core) | Always, when this pack is on: the seven safety rules. |
| `packs/wheelhouse/guide.md` | Interview (sections 1–2), generating the package (all of it), and before any story that reads or changes Wheelhouse data (the sections that story touches). |
| `packs/wheelhouse/stories.md` | Generating the package, and adding a feature that brings Wheelhouse in. |

## By skill

- **`start-project-method`:** say the Wheelhouse sentence from `references/scope.md` once. Ask whether the project only reads from Wheelhouse or changes things there (Q-CONNECT-2). How it gets its data follows the shape the answers point to (Q-CONNECT-3, `references/shape.md`, guide §2): through Claude when they ask; a page Claude builds and refreshes for a team, when asked or on a schedule in Cowork (no key); or software with an API key when it must not depend on Claude, feed another system, or be used by people outside Claude. The answers decide, not how technical the person seems, and the owner has the final say. If the connector is connected and the person agrees, you may look at a few of their listings, **read only**, to understand their account (how many listings, multi-unit or not, which channels) and use that to ask better questions. Say what you looked at. Never change anything during the interview.
- **`generate-package`:** copy the seven rules from `references/wheelhouse.md` into the project's `CLAUDE.md` (and `SAFETY.md` if it changes things). Write the facts the project needs from `guide.md` into `GUIDE-reference.md` under "Wheelhouse", with the date each was checked, and a "Gotchas" line in `CLAUDE.md` for each surprise that applies (§4 and §5). Add the early stories from `stories.md` that apply.
- **`next-story`:** before a story that touches Wheelhouse, read the guide sections it touches. Check facts against the live documentation or real data when the story depends on them; if what you see differs from the guide, trust what you see, write it under "Gotchas" in `CLAUDE.md`, and tell the owner.
- **`add-feature`:** if a feature brings Wheelhouse in, or changes from reading to changing, add the matching stories from `stories.md` to the feature.

## What it never does

- Change anything in a Wheelhouse account during the interview or planning.
- Ask for the person's Wheelhouse password or API key in the chat.
- Treat this guide as more current than Wheelhouse's own documentation. The API is in beta; the documentation and real data win.
