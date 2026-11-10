# How it is used and kept up to date (the shape)

Every project ends up in one of a few shapes. The shape decides how it gets built and where, so it is settled in the interview (Q-CONNECT-3), written in the brief with the reason and what would change it, and checked again whenever something is added. The person's answers decide it, never how technical they seem, and the owner has the final say. This applies to every project, whatever it connects to (Wheelhouse, another system, files, or nothing).

## The shapes, in three tiers

| Tier | Shape | What it is | Where it can be built |
|---|---|---|---|
| 1 | **With Claude, when asked** | Claude produces the answer, report or change each time the person asks, using their files or connectors | Anywhere: the Claude website, Chat in the desktop app, Cowork, Claude Code |
| 1 | **A finished document or file** | A guide, report, handbook or spreadsheet handed over | Anywhere |
| 1 | **A page a team uses** | A page (a Claude artifact) shared with others, showing a saved copy that Claude refreshes when the owner asks | Anywhere |
| 2 | **Claude refreshes it on a schedule** | The same page or report, refreshed by a scheduled Claude task (for example every morning) instead of by the owner asking. Still through Claude and the owner's connectors, so no key | The desktop app (Cowork). The computer must be on when the schedule fires (it can be asleep, from what has been seen) |
| 3 | **Software that runs without Claude** | A website or app (hosted somewhere like Vercel, or on their own site), a script on a server, something that feeds another system. Claude is the developer, building it one reviewed step at a time | The desktop app (Cowork) or Claude Code, with a folder. A key goes in a private file where a system needs one; putting it online gets a clear yes first |

The tiers are steps, not separate paths: a project can start in tier 1 and move up when a "Check again if" signal comes up. Moving keeps the plan and what is built; it adds stories.

## Choosing from the answers

Take the smallest tier that meets every need the answers name, and say which answer led there: *"Because you said your two colleagues need to see it, but weekly when you ask is fresh enough, I suggest a page your team uses, which I refresh when you ask."*

- Just them, when they ask → with Claude, when asked.
- Something to read, print or send → a finished document or file.
- Others need to look at it or work with it, and "when I ask" is fresh enough → a page a team uses.
- It must stay fresh with nobody asking, and depending on the owner's computer and Claude is fine → Claude refreshes it on a schedule.
- It must not depend on the owner's computer or Claude; people outside Claude (customers, owners, the public) use it; it sends results into another system; or more people need to change it, not only look → software that runs without Claude.

When nothing points further, suggest the simplest that fits. If the owner wants a different shape, record their choice and their reason. For Wheelhouse data, the pack's guide (§2) says what each shape means there.

## Where they work follows the shape

Tier 1 works anywhere, including on the Claude website. Tiers 2 and 3 need the desktop app (Cowork), or Claude Code for tier 3. If the shape needs Cowork and they are working in chat, say so at the read-back and offer the move (`references/chat-mode.md`, "Moving to Cowork"); planning can carry on in chat.

## What would change it

Write the brief's "Check again if" from the answers, as plain signals. The usual ones:
- it must update itself with nobody asking (tier 2, or 3 if it can't depend on their computer);
- people outside Claude need to use it (tier 3);
- it must send results into another system (tier 3);
- more people need to change it, not only look at it (tier 3).

## Checking it as the project grows

- **When a new idea comes in** (`add-feature`) **and before each story** (`next-story`), compare what is being asked with "Check again if". Typical moments: "can it update itself every morning?", "can our owners log in to see it?", "can it push the results into our other system?".
- **When one is met, stop and raise it as a decision** (`review-gate`): what the request needs; why the current shape can't do it well; the choices, smallest first (keep the shape and do it another way, for example "I refresh it when you ask"; move up one tier; or more); and what each costs: which stories it adds, whether it needs Cowork, the computer on, or a key. Give a recommendation, then wait.
- **Never switch silently, and never carry on past it silently.** Squeezing a tier 3 need into a page, or skipping straight to tier 3 when a scheduled refresh would do, is the mistake this check exists to prevent.
- **On a yes to change:** record the decision in the plan's decisions table and the brief (new shape, why, new "Check again if"), add the stories the new shape needs as a plan change (with the owner's yes, as always), and log it. Nothing already built is thrown away without saying so.

## When you outgrow this

Every plan in tiers 1 and 2 ends with a short note: what would mean it's time to change shape (the brief's "Check again if"), and what the next tier would add. It's a signpost, not a plan: no stories are written for it until the owner asks.
