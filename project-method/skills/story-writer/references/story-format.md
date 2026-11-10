# How to write a story

A story is one small piece of work, sized so it can be finished and checked in a single working session. The exact shape is in `templates/parts/story-format.md`; this page says how to fill it in well.

## The parts, and what good looks like

**Name.** A plain phrase for the outcome ("Send the request email"), not the activity ("Work on emails").

**Reads first.** Only what this story needs: the rules file, the last log entries, and the specific guide sections. A story that says "read everything" is too vague or too big. A file made by an earlier story may be named, as long as that story's Build list names it.

**Build.** A short list of concrete outcomes someone could check ("a request email goes to the tool's owner and nobody else"), not step-by-step instructions. State what is *not* being built when the boundary matters.

**Tests.** The checks that prove it works, and **at least one check deliberately broken to prove it can fail**. For data work: the hand-worked sample and the independent source. For documents: the checklist from the brief and the fresh-eyes read. Say how the result will be *used* by a person, not only inspected.

**Done when.** One observable result that ends the argument: "the owner has seen the exact email in the test inbox and said yes", not "email works".

**Prompt.** The instruction to paste into a session, in plain words: what to read, what to make, what to avoid, what to check, and where to stop. It should work in a cold session with no other context.

## Size

A story fits one sitting if you can describe its result in one sentence and its checks in a short list. Split a story when:
- it has more than one "done when";
- it touches both something new and something risky (do the risky part alone);
- the checks need real data and the build does not (separate "build on made-up data" from "connect to the real thing");
- a person has to look at something halfway through (that is a review gate, so the story ends there).

## The two marks

Both marks go after the story number: `### Story 2.3 ★ STOP FOR REVIEW — …`, `### Story 2.3 ⚠️ — …`.

**★ STOP FOR REVIEW.** Put it on any story whose result a person should see before more is built on it: the first look at anything visual, a sample document, a first set of results, a definition that numbers will rest on. The session ends with a summary, how to look at it, the decisions needed with a recommendation each, and waits.

**⚠️ Needs extra care.** Put it on any story where a silent mistake would be costly: it changes real data, sends something to real people, spends money, produces numbers people will act on, or cannot easily be undone. Say why in one sentence, on the same line as the warning. These stories get a stronger model or extended thinking, a test inbox or sandbox first, and a fresh yes before anything real.

## Order

- Foundations first (how to run, check and log), then a first version on made-up data, then the real features, then real connections, then the full check.
- Open questions are answered by their own early stories, with evidence, before work that depends on the answer.
- Anything outward-facing comes last, behind a gate.
