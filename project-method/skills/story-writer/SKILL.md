---
name: story-writer
description: "Writes or tightens a single story in the house format: what to read first, what to build, a paste-ready prompt, the tests, a done-when, and a complexity flag when a silent mistake would be costly. Use when a story is missing, vague or too big and needs splitting, or when the user says 'write a story for', 'break this down', or 'this story is too big'. Used by generate-package and add-feature."
user-invocable: false
---

# story-writer

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

You write one story (or split one that is too big) so that a session with no memory of anything else can pick it up and finish it. The exact shape is `templates/parts/story-format.md`; how to fill it well is `references/story-format.md`. Read both. A worked example for each project type is in `templates/examples/`.

## Write it

Every story has, in this order:

1. **A heading:** `### Story <phase>.<number> — <plain name of the outcome>`. Marks go after the number: `### Story 2.3 ★ STOP FOR REVIEW — …` if it ends at a review gate, `### Story 2.3 ⚠️ — …` if it needs extra care, or both.
2. **If ⚠️:** the line `> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here):` followed, **on the same line**, by one sentence saying why a quiet mistake would be costly here.
3. **Reads first:** only the files and sections this story needs. Every file named must exist in the project or be made by an earlier story (whose Build list names it).
4. **Build:** a short list of concrete outcomes someone could check, not steps. Say what is deliberately not being built when the boundary matters.
5. **Tests:** how we will know it works, including **one check broken on purpose to prove it can fail**, and how a real person would use the result. For data work: a hand-worked sample and an independent source. For documents: the brief's checklist and a fresh-eyes read. Pick the layers from the testing reference for the project's type (`references/testing-layers-software.md`, `references/testing-layers-data-analysis.md` or `references/testing-layers-other.md`), as much as its size calls for; for anything that changes something real, add the checks from `references/safety-patterns.md`.
6. **Done when:** one observable result that ends the argument ("the owner has seen the exact email in the test inbox and said yes").
7. **Prompt:** a ready-to-paste block in plain words: what to read, what to make, what to avoid, what to check, and where to stop. It must work in a cold session. End with writing the log entry, and stopping at the gate if there is one (for a ★ story, the log entry comes after the owner answers). If the story makes a file that later stories read, name it in the Build list.

## When to add the marks

- **★ STOP FOR REVIEW** when a person should look before more is built on it: the first look at anything visual, a sample document, first results, a definition that numbers will rest on, the first real change.
- **⚠️ Needs extra care** when a quiet mistake would be costly: it changes real data, sends something to real people, spends money, produces numbers people will act on, or is hard to undo.
- A story that makes the first real change to anything is always both, stands alone, reads `SAFETY.md`, and needs a fresh yes from the owner.

## Size, and splitting

A story fits one sitting when its result fits in one sentence and its checks in a short list. Split it when:
- it has more than one "done when";
- it mixes something new with something risky (do the risky part alone);
- it builds on made-up data **and** connects to the real thing (two stories);
- someone has to look at something halfway through (the story ends there, as a ★).

When you split, keep the original number for the first part and number the rest next (2.3 becomes 2.3 and 2.4, and later stories move up by one only if they have not started). Say in the log what was split and why. Do not renumber stories that the log already records as started or done.

## Check your story

Before handing it back: all seven parts present; the prompt is a fenced block of at least a dozen words and makes sense on its own; every file in "Reads first" exists; a ⚠️ has its reason; it does not build anything out of scope or from "later"; it is written in plain words.

## What not to do

- Do not write steps for their own sake; write outcomes and checks.
- Do not hide a risky change inside a bigger story.
- Do not write a prompt that depends on this conversation; the next session will not have it.
- Do not renumber finished or started stories.
