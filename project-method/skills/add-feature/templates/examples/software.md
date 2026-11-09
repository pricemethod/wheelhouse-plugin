# Worked example: software (an invented project, "Corner Tool Share")

Use this as a model for what good stories look like. It is not a template to copy: write stories from the user's own brief.

**The brief in one line:** a simple website where neighbors list tools they will lend and ask to borrow tools from each other. It sends emails, so it can change real things.

**Why the stories look like this:** the first look at the real screens comes early and stops for review; the one story that sends real emails is flagged and tried on a test inbox first; the fake-data version comes before any real connection.

### Story 1.1 ★ STOP FOR REVIEW — A first look at the tool list, on made-up data

**Reads first:** `PROJECT_BRIEF.md` (who it is for, look and feel), `GUIDE-design.md`.

**Build:**
- The tool list screen and the single-tool screen, filled with about a dozen believable made-up tools and neighbors.
- A loading look, an empty look ("No tools yet. Be the first to share one.") and a trouble look, used the same way everywhere.
- It works at phone width and desktop width.

**Tests:** the screens show the made-up tools; the empty and trouble looks appear when asked; every button is big enough to tap; break the empty-look check on purpose and confirm it fails, then restore it.

**Done when:** the owner has looked at both screens on a phone and a computer and has said what to change.

**Prompt:**
```
Read the rules file, the last log entries, PROJECT_BRIEF.md and GUIDE-design.md. Build the tool list and single-tool screens on believable made-up data, with a loading, empty and trouble look. Check them at phone and desktop width, run the checks, break one on purpose and restore it, write the log entry, and then stop and show the owner how to look at them. Do not connect anything real.
```

### Story 2.3 ⚠️ — Send the "someone wants your ladder" email

> ⚠️ **Needs extra care** (a stronger model or more thinking time helps here): This sends real email to real neighbors: a mistake emails the wrong person, or emails twice.

**Reads first:** `SAFETY.md`, `GUIDE-reference.md` (the email service), the log entries for the borrow-request story.

**Build:**
- One doorway in the code that every outgoing email must pass through, which refuses anything not on the approved list while testing.
- The request email, sent to the owner of the tool and nobody else, at most once per request.
- A test inbox used for every check until the owner says otherwise in writing.

**Tests:** sending twice for one request sends one email; a request for someone else's tool never reaches the wrong person; the doorway refuses a non-test address; break the doorway on purpose and confirm the refusal check fails; read the real email in the test inbox and check the wording.

**Done when:** the owner has seen the exact email in the test inbox and has said yes, in writing, before any real neighbor is emailed.

**Prompt:**
```
Read SAFETY.md, GUIDE-reference.md and the borrow-request log entries. Build the single doorway every outgoing email passes through, then the request email to the tool's owner only, once per request, sending only to the test inbox. Run every check in the story, break the doorway check on purpose and restore it, and read the real email in the test inbox. Do not email any real neighbor. Write the log entry and stop for the owner's yes.
```

### Story 3.1 — Answer the open question about proving a neighbor lives here

**Reads first:** `PROJECT_BRIEF.md` (open questions), the decisions table in `PLAN.md`.

**Build:**
- The two or three realistic ways to confirm a neighbor lives on the street, each with what it costs the neighbor in effort.
- A recommendation, and the exact edit the decisions table needs.

**Tests:** each option is checked against what a neighbor actually has (an email address, a street name, a code from the owner); the owner has picked one.

**Done when:** the decisions table has an answer, or the owner has moved the question to "later".

**Prompt:**
```
Read the open questions in PROJECT_BRIEF.md and the decisions table in PLAN.md. For the question about proving a neighbor lives on the street, lay out two or three realistic options, what each asks of a neighbor, and your recommendation. Do not build anything. List the exact decisions-table edit under "Plan updates needed", write the log entry, and stop.
```
