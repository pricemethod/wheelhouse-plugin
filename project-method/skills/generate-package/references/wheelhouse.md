# When a project uses Wheelhouse data

Project Method is published by Wheelhouse, and many people using it will want to build on their own Wheelhouse data: a report of their occupancy, a tool that suggests prices, a guide that shows their rates. These rules apply whenever a project **reads or changes anything in a Wheelhouse account** (listings, prices, reservations, custom rates, minimum stays or other settings). They are a small first set; they do not replace Wheelhouse's own guidance.

## How to reach the data

- **The Wheelhouse pack** (`packs/wheelhouse/README.md`) has the details: where to look things up, how a project gets its data, which follows its shape (`references/shape.md`): with Claude when asked; a page a team uses, which Claude refreshes; or on its own, with a key, the surprises seen in real data, and the early stories a plan needs. It switches on whenever the brief lists Wheelhouse (`references/scope.md`).
- **Wheelhouse's other skills:** if the person has other Wheelhouse skills in Claude, use them where they fit; Claude can see what is installed. Project Method never depends on them.
- **Signing in:** the Wheelhouse connector signs in with the person's Wheelhouse account. Never ask for a password or an API key in the chat. If the project needs a key (for example software that runs without Claude), say where the key file goes and let the person put it there.
- **Facts about Wheelhouse come from Wheelhouse:** the API documentation (`api.usewheelhouse.com/wheelhouse_rm_api`) and what the data actually returns. Do not guess field names or behavior; check, and say what you checked.

## The rules

1. **Reading is fine; changing is a real change.** A project that changes anything in Wheelhouse can change something real: Q-CONNECT-2 is "yes", the plan is never smaller than Standard, and it gets a `SAFETY.md` and the safety stories.
2. **Never change a real listing without a clear yes** to that exact change (which listing, which dates, which value), every time. An earlier yes doesn't carry over.
3. **Try it on one first.** The first change goes to a single listing, a test listing if the account has one, otherwise one listing the owner picks, and is checked before anything wider.
4. **Read before you change.** Fetch the listing's current settings immediately before changing them. Some Wheelhouse settings are lists that are replaced whole: sending only the new item deletes every item left out. Always carry forward what you're not changing.
5. **Check what happened.** After a change, read it back and look for warnings or partial results; a "success" reply alone is not proof. Tell the owner exactly what changed, and anything that didn't.
6. **Keep account details out of the log and the chat** where they aren't needed: guest names and contact details are personal details (house rule: protect personal details).
7. **A page never reaches into Wheelhouse by itself.** A page or dashboard that other people open shows a saved copy that Claude refreshes when the owner asks; the page itself never connects to Wheelhouse. Only a page just for the owner, looking at their own data while they watch, may use the Wheelhouse connector directly, and only after telling them plainly that allowing it lets the page do anything the connector can, changes included. Either way the page only reads (pack guide §2).

## Where these rules go

- **The interview (`start-project-method`):** when someone mentions Wheelhouse (their prices, listings, reservations or settings), write "Wheelhouse" under systems with the scope (`references/scope.md`), and ask whether it only reads from Wheelhouse or changes things there.
- **The package (`generate-package`):** copy the seven rules into the project's `CLAUDE.md` (under the safety rules) and, if it changes things, into `SAFETY.md`. The first story that touches Wheelhouse only reads, and shows the owner what came back (the pack's Story A).
- **Building (`next-story`):** before a step that reads or changes Wheelhouse data, follow this file and the pack's guide sections that step touches.
