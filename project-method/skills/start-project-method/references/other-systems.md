# Working with any other system

For any outside system the project uses that has no pack of its own: a property management system (Guesty, Hostaway and the like), an accounting tool, a spreadsheet service, an email or text service, or a connector the person has added to Claude. Work through these with the owner, in plain words, and write what you find in `GUIDE-reference.md` under that system. Never guess; check, and say what you checked.

## 1. Find its own instructions

- Look for the system's official API or developer documentation and its help center, and write the links in `GUIDE-reference.md`. Use only what the system itself publishes, or what its real data shows; never a blog post's guess.
- If the person has a connector for it in Claude, say so: it is the easiest way to look at real data. If not, the project can still use the system through its documented API, or through a file the person exports.
- If you cannot find its documentation, say so plainly and make finding it an open question, answered before any story depends on the system.

## 2. How it signs in

- Find out from its documentation how a program signs in (an API key or token, a sign-in through the connector, a username and password) and whether a read-only key exists. Prefer read-only whenever the project only reads.
- **Never ask for a password, key or token in the chat.** Say where the private file goes in the project (a file listed in the rules as never shared or saved to history) and let the person put it there. If they paste one by mistake, tell them to make a new one in that system and not to use the pasted one.
- Keys for different systems go in different files, named for the system.

## 3. Its limits

- How many requests it allows in a minute or a day, and what it does when you go over. Read the limit from the system's replies where it gives one, rather than writing a number into the project.
- How long lists come back (pages), and the most per page.
- Anything its documentation marks as beta or changing.

## 4. Read only, first

- The first story that touches the system **only reads**, and shows the owner a small sample of what came back (with personal details left out). Nothing is planned on a field until it has been seen in real data.
- Write what you saw in `GUIDE-reference.md`: the fields the project needs, what they really hold, and any surprise (a field that is empty, a date in a different form, money in cents). Real data beats documentation; note where they differ.

## 5. Changing anything there

Changing anything in another system is a real change, the same as for Wheelhouse: Q-CONNECT-2 is "yes", the plan is never smaller than Standard, the project gets `SAFETY.md`, and the same rules apply: read before you change, a clear yes for each exact change, try it on one first (a test record or test account if the system has one), and check what happened afterwards. Follow `references/before-outward-actions.md`.

## 6. Personal details

Systems like these hold guest names, contact details, addresses, door codes and payments. Keep them out of the chat, the log and the plan. Show samples with those fields left out.
