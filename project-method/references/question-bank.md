# Question bank for the intake interview

The questions `start-project-method` asks, in order, in eight groups. Each question says what it is for, gives an example and a recommended answer, and says exactly what to do if the person answers "I don't know". The skill's behavior lives in `skills/start/SKILL.md`; this file is the content, so it can be improved without touching the skill.

**How to read an entry**

- **Group:** which of the eight groups (the interview asks a group at a time, never more than four questions at once).
- **Fills:** the brief field(s) the answer goes into (`none` for a question that only confirms something).
- **Types:** which project types it applies to: `all`, or any of `software`, `data-analysis`, `other`.
- **Ask:** the question, in plain words, as it should be said. Where the wording differs by project type there is an `Ask (type)` line.
- **Why we ask:** the reason, so the person can be told if they wonder.
- **Example:** an invented example to show what a good answer looks like.
- **Recommended:** the answer to suggest if the person is unsure.
- **Unknown:** what to do on "I don't know". Any of: `block` (it must be answered to continue: help with examples; if it stays unknown, offer to stop and resume later), `open-item` (record it as an open question to answer in an early story), `default: <text>` (use that text). Separated by semicolons.

**Rules for every question**

- Ask in plain words. Explain any term the first time (see `references/glossary.md`).
- Offer the example and the recommended answer; never push them.
- After each group, say it back in one or two sentences and ask "Did I get that right?" before moving on.
- Never ask for a password, key or private detail. If a system needs one, say where it will go later (a private file) and move on.
- "I don't know" is a fine answer. Apply the **Unknown** rule, say so kindly, and carry on.
- **Ask each question once.** The four in group 7 (what is out or for later, the worst that could go wrong, special words, what you are unsure about) are asked only there, as a short wrap-up. If the person mentions one of them earlier, note it in the brief and carry on; in group 7, read back what you noted and ask only whether to add anything.

## Group 1: The idea

### Q-IDEA-1 — What and for whom
- **Group:** 1
- **Fills:** project_name, one_liner
- **Types:** all
- **Ask:** "In your own words, what would you like to make, and who is it for? Don't worry about getting it perfect; a rough sentence is fine."
- **Why we ask:** Everything else is built on this. The name and the sentence appear at the top of every file.
- **Example:** "A simple weekly page showing which of my listings are pacing behind last year, and why, so I know where to adjust prices. I'll call it Pace Watch."
- **Recommended:** If there is no name yet, suggest a plain working name from their sentence and say it can change.
- **Unknown:** project_name: default: Untitled project (working name); one_liner: block

### Q-IDEA-2 — Who decides, and how much to explain
- **Group:** 1
- **Fills:** owner_name, comfort_level
- **Types:** all
- **Ask:** "Who will make the decisions about this project? That is usually you. And as we go, would you like me to explain everything in plain words, or keep it brief?"
- **Why we ask:** The owner approves the plan and says yes at every pause. The second part only tunes how much is explained; it never limits what can be built.
- **Example:** "Me, Dana Whitfield. Please explain things; I'm not technical."
- **Recommended:** The person you are talking with, and plain words with every term explained.
- **Unknown:** owner_name: default: The project owner; comfort_level: default: Plain words, and explain every term the first time

### Q-TYPE-1 — The kind of project
- **Group:** 1
- **Fills:** project_type
- **Types:** all
- **Ask:** "Which of these is closest? (a) Something people will use, like a website, a tool or an app. (b) Looking into information to answer a question, like an analysis or a set of figures. (c) Something else, like a report, a document, a guide or a process."
- **Why we ask:** It decides how the plan is shaped and how the work is checked.
- **Example:** "Which months booked late last year, to set minimum stays" is (b). "A pricing playbook for new revenue managers" is (c).
- **Recommended:** Pick the main one. If it is a mix, choose what the person will mainly receive, and note the rest as part of the scope.
- **Unknown:** block

## Group 2: Who it is for and what success looks like

### Q-WHO-1 — The people
- **Group:** 2
- **Fills:** audience
- **Types:** all
- **Ask (software):** "Who will use this, and how will they usually get to it: on a phone, at a desk, somewhere busy?"
- **Ask (data-analysis):** "Who will read or act on the answer, and what decision will they make with it?"
- **Ask (other):** "Who is this for, and where will they read or use it?"
- **Why we ask:** It decides tone, size of buttons or length of text, and what to leave out.
- **Example:** "Me and two revenue managers, at our desks on Monday mornings."
- **Recommended:** Name one main group first; extra groups can be added later.
- **Unknown:** open-item

### Q-WHO-2 — Success
- **Group:** 2
- **Fills:** success_definition
- **Types:** all
- **Ask:** "Imagine it is finished and working well. What can someone do, or know, that they could not before? How would you tell it worked?"
- **Why we ask:** It is the test every story is judged against.
- **Example:** "On Monday I open it, see the five listings furthest behind last year and why, and have my price changes decided in under fifteen minutes."
- **Recommended:** One sentence about a single thing a person can do, ideally something you could time or count.
- **Unknown:** open-item

## Group 3: What is in

### Q-SCOPE-1 — What is in
- **Group:** 3
- **Fills:** in_scope
- **Types:** all
- **Ask:** "What are the main things it has to do or contain? A short list is perfect, three to six items."
- **Ask (data-analysis):** "What exactly do you want to find out? Please include the exact dates or periods to look at, for example 'June to August 2025 compared with the same months in 2024'."
- **Why we ask:** This is the scope the plan is built from. Anything not on the list waits for a decision.
- **Example:** "Each listing's booked nights and average nightly rate against last year; the ones furthest behind first; a likely reason (price, minimum stay, few searches); a list of changes to consider."
- **Recommended:** Start small. If the list is long, ask which ones would make it useful on their own.
- **Unknown:** block

## Group 4: What it connects to, and whether it changes anything real

### Q-CONNECT-1 — Other tools, accounts and information
- **Group:** 4
- **Fills:** systems, data_sources
- **Types:** all
- **Ask:** "Will it need to use anything that already exists: another website or service, an account, a spreadsheet, a set of files, a list of people? If so, what?"
- **Why we ask:** Connections are where surprises hide. Each one gets checked early, in its own step.
- **Example:** "Our pricing tool, for bookings and prices. A spreadsheet of each owner's minimum price."
- **Recommended:** List each thing separately, even if it feels small. "None" is a fine answer. Put a service or system it uses while it runs (an email service, a booking system, a website) under systems; put a file someone hands over (a spreadsheet export, a document) under data and files. Ask whether any of those files hold personal details (names, phone numbers, addresses, door codes), and note it. If they know the kind of thing but not which one ("whatever sends the texts"), write it as the kind with "(not chosen yet)" and add choosing it as an open question. If they mention Wheelhouse (their prices, listings, reservations or settings), write "Wheelhouse" under systems and follow `references/wheelhouse.md`. For each system, note what it is used for and which guide covers it, and end the line with the scope, as `references/scope.md` shows ("Wheelhouse (prices; Wheelhouse pack); Guesty (payouts; other-systems guide) [scope: Wheelhouse plus other systems]"). If more than one system holds the same properties or bookings, ask which one is right for each fact (`references/joining-systems.md`).
- **Unknown:** systems: default: None; data_sources: default: None

### Q-CONNECT-2 — Can it change anything real
- **Group:** 4
- **Fills:** real_world_changes
- **Types:** all
- **Ask:** "Will it send, publish, delete or change anything outside this folder, like emailing people, updating a list someone else uses, or posting something? Or does it only read and produce results for you?"
- **Why we ask:** Anything that changes real things gets extra safety rules, a bigger plan, and a pause before each real change.
- **Example:** "Yes: it updates prices in our pricing tool." Or "No: it only reads and shows me the list."
- **Recommended:** If unsure, say yes. It is safer to assume it can change things until we find out. If the person proposes a real change (for example "can you also email it to everyone?"), explain in plain words what it adds: a bigger plan with safety steps, a way to send, and the list of people. If they then decide against it, add the declined action to "out of scope", and record "no" here only if that was the only real change (otherwise "yes" stands for the others).
- **Unknown:** default: yes: not confirmed yet, so treated as yes (the safe choice) until we find out; open-item

### Q-CONNECT-3 — How it will be used and kept up to date
- **Group:** 4
- **Fills:** shape, shape_reason, shape_switch_if
- **Types:** all
- **Ask:** "Once it's done, how will it be used? For example: you ask me for it when you need it; it's a finished document or file; your team opens a page you share; it has to keep itself up to date every day with nobody asking; or people outside, like customers or owners, use it on its own website. And how fresh does it need to be?"
- **Why we ask:** This decides how it gets built and where: here with me, as a file or a page your team can open, refreshed by me on a schedule, or as its own software that I build with you. Getting it right now saves rebuilding it later, and it can change as the project grows.
- **Example:** "My two colleagues should be able to look at it any time. Updated once a week is fine; I'll ask for it."
- **Recommended:** Suggest the smallest shape that meets every need the answers name (`references/shape.md`), and say which answer led there. Just them, when they ask: with Claude. Something to hand over: a finished file. A team that only needs to look, fresh when asked: a page Claude refreshes. Fresh every day with nobody asking: Claude refreshes it on a schedule (Cowork; the computer must be on). People outside Claude use it, it feeds another system, or it must not depend on their computer: software that runs without Claude (Cowork or Claude Code). When nothing points further, the simplest that fits. The owner decides; if they want something else, record their choice. Write down what would change it (shape_switch_if), using the answers ("if it has to update every morning on its own").
- **Unknown:** shape: default: worked out from the other answers, with the reason, and checked again at the read-back; shape_reason: default: worked out from the other answers; shape_switch_if: default: it must update itself with nobody asking, people outside Claude need to use it, or it must send results into another system

## Group 5: Look and feel

### Q-LOOK-1 — The feel
- **Group:** 5
- **Fills:** look_and_feel
- **Types:** all
- **Ask (software):** "How should it look and feel? Friendly or serious, bright or calm? Is there a website or app whose feel you like?"
- **Ask (data-analysis):** "How should the results look when you receive them: a short summary, charts, a table? Who needs to read it, and how?"
- **Ask (other):** "What should it read like: warm and short, formal, step by step? Is there something you have seen that is the right tone?"
- **Why we ask:** It sets the style guide, so every part is made in the same way.
- **Example:** "Clean and calm, numbers easy to scan, behind in orange and ahead in green. Like our pricing tool's dashboard, only simpler."
- **Recommended:** Name one thing you like as a reference. For a document, ask what format they need in the end (a Word file, a PDF, printed pages, an email). Also mention, if they apply: needs such as large print, screen readers or colors that work for color-blind readers; which language or languages; and any logo, colors or wording you already use.
- **Unknown:** open-item; default: Plain and friendly, to be decided with the owner after a first look

### Q-LOOK-2 — Devices
- **Group:** 5
- **Fills:** devices
- **Types:** software
- **Ask:** "What will people use it on: phones, tablets, laptops? Which matters most?"
- **Why we ask:** It decides the screen sizes everything is built and checked on.
- **Example:** "Phones first, and a desktop browser too."
- **Recommended:** If most people will be out and about, say phones first.
- **Unknown:** default: Phones and computers

## Group 6: Limits, and how we will work

### Q-LIMITS-1 — Constraints
- **Group:** 6
- **Fills:** constraints, deadline
- **Types:** all
- **Ask:** "Is anything fixed in advance: a deadline, a budget, tools you must or must not use, or someone who has to approve the result? If there is a deadline, which exact date?"
- **Why we ask:** Limits shape what is realistic and when the pauses should happen.
- **Example:** "Free or very cheap to run. A first version before the summer season, by 2027-05-15. I review everything."
- **Recommended:** Say the date that matters most (as an exact day; "by the 1st" means which month?) and who has the final word. If it will need looking after once it is finished (updates, answering questions), say who will do that.
- **Unknown:** constraints: default: None stated; deadline: default: None

### Q-WORK-1 — Pauses and snapshots
- **Group:** 6
- **Fills:** review_cadence, commit_policy
- **Types:** all
- **Ask:** "How often should I stop to show you my work: after every step, or only at the big moments (the planned review stops)? Either way I always stop before anything is sent or changed. And should I save a snapshot of the project (a copy we can go back to) after each step, or only when you ask?"
- **Why we ask:** The pauses are where you steer, and some people prefer to control snapshots themselves.
- **Example:** "After every step. Snapshots only when I ask."
- **Recommended:** After every step; save snapshots only when you ask. Record the answer as exactly "After every step" or "Only at the big moments", and "Only when asked" or "After each step", so the plugin's helpers read it the same way.
- **Unknown:** review_cadence: default: After every story, and always before anything is sent or changed; commit_policy: default: Only when asked

## Group 7: Last few things (a short wrap-up)

Four quick questions, asked once, here and nowhere else. If the person already mentioned any of these, read back what you noted ("Earlier you said no payments; anything else to rule out?") instead of asking from scratch.

### Q-SCOPE-2 — What is out, and what is for later
- **Group:** 7
- **Fills:** out_of_scope, later_ideas
- **Types:** all
- **Ask:** "A few last quick ones. Is there anything you are sure you do NOT want? And any ideas you like but would rather park for later? Parked ideas are not lost; they go on a list."
- **Why we ask:** Saying no up front stops the project from quietly growing, and parked ideas have a safe place to wait.
- **Example:** "It never changes prices itself. Later, maybe a weekly email of the list."
- **Recommended:** Suggest two or three things commonly assumed for this kind of project and ask whether to rule them out; move anything not essential for a first useful version to "later".
- **Unknown:** out_of_scope: default: Nothing decided yet. Anything not listed as in scope waits for a decision; later_ideas: default: None yet

### Q-NEVER-1 — The costly mistakes
- **Group:** 7
- **Fills:** never_events
- **Types:** all
- **Ask:** "What is the worst thing that could go wrong with this? What would you hate to see happen?"
- **Why we ask:** It becomes the first rule in the rules file and, where real things can change, the safety file.
- **Example:** "A price set below an owner's minimum; a change made to the wrong listing; totals that mix two currencies."
- **Recommended:** Think about wrong numbers, wrong people, private or personal information, and anything that cannot be undone.
- **Unknown:** open-item; default: Nothing specific named yet. Ask the owner before any change that cannot be undone.

### Q-WORDS-1 — Words that mean something special
- **Group:** 7
- **Fills:** key_terms
- **Types:** all
- **Ask:** "Are there words you use for this project that someone new might not understand? For example, what you call the people, the parts or the steps."
- **Why we ask:** They go in the glossary, so everyone means the same thing by them.
- **Example:** "Pacing: how bookings so far compare with the same point last year. ADR: the average price per booked night."
- **Recommended:** Include any word you use that has a special meaning for you.
- **Unknown:** default: None yet. Words are added to the glossary as they come up

### Q-RISK-1 — Open questions
- **Group:** 7
- **Fills:** open_items
- **Types:** all
- **Ask:** "Last one: what are you unsure about, or what do you wish you knew before starting? Each one will get answered early, in its own step."
- **Why we ask:** Unanswered questions are the most common reason a plan goes wrong. Naming them lets us answer them first.
- **Example:** "Do we compare last year by booking date or by stay date? Can it read our pricing tool automatically?"
- **Recommended:** Include anything you said "I don't know" to earlier; those are added automatically.
- **Unknown:** default: None yet

## Group 8: Putting it together

### Q-CONFIRM-1 — The size of the plan, and the read-back
- **Group:** 8
- **Fills:** size, size_reason
- **Types:** all
- **Ask:** "I suggest a **{size}** plan, because {reason}. Here is everything you have told me, on one page. What is wrong or missing, and does that size sound right? When it is right, say so and I will turn it into your project plan."
- **Why we ask:** A small idea should not get a large plan and a risky one should not get a small plan; and nothing is generated until the owner confirms the brief.
- **Example:** "Standard is fine. Change 'phones first' to 'phones only'."
- **Recommended:** The size worked out by the rules below. In the read-back, also say how it will be used and kept up to date, and which answers led there (Q-CONNECT-3), so that is confirmed too. A project that can change real things is never smaller than Standard; if asked for smaller, explain why and keep Standard. Read the brief slowly; this is the cheapest moment to change anything.
- **Unknown:** size: default: the size worked out by the rules; size_reason: default: the reason worked out by the rules

## Choosing the size

Work it out from the answers (never ask the person to choose cold; propose, with the reason):

**"Something outside"** means a system, service or account the project uses while it runs: an email or text service, a booking system, a website, a shared online sheet. A file someone hands over once (a spreadsheet export, a Word document) is not something outside; it is information the project uses.

- **Lite:** about four things or fewer in scope, nothing outside it to connect to, and nothing that changes anything real. A small, low-risk idea; eight stories or fewer.
- **Standard:** more than four things in scope, **or** it connects to something outside, **or** it can change anything real (this last one is never smaller than Standard).
- **Full:** about eight things or more in scope **and** it connects to two or more outside things or can change something real; or it can change real things **and** connects to three or more outside things. Many parts, real consequences.

If the person asks for a different size, record their choice and the reason, except that a project that can change real things stays at Standard or larger. Write the size as one exact word (lite, standard or full) and the reason, in a plain sentence, under "Why this size".

## Choosing the project type

Pick the one the person will mainly receive: something people use (**software**), figures and findings from looking into information (**data-analysis**), or a document, guide or process (**other**). A mix is classified by its main deliverable, and the rest is written into the scope.

## The quick version (small, one-time things)

The full interview suits something the person will keep using or build on. For a small thing made once (a one-off report, a single document, a list for one event), offer a shorter path. After group 1, if the idea sounds like that, say so in one line and offer it: *"This sounds like a one-time thing. Want the quick version? About ten questions and a short plan. You can switch to the full set at any point."* Never push it; the full set is always fine.

- **It asks:** group 1; Q-WHO-2 (success, the question that matters most); Q-SCOPE-1; group 4; then Q-NEVER-1 and Q-RISK-1 as the wrap-up; then group 8.
- **Everything else takes its Unknown default,** written as a default in the brief, not as an open question. Say once, at the read-back, that those were left at their usual answers and can be changed.
- **Switch to the full set** (say why in one sentence) as soon as the answers show it connects to a system it uses while it runs, can change anything real, or has more than four things in scope. Those need the questions the quick version skips.
- **The size is Lite.** Write "quick version" in "Why this size", and keep the progress line saying so: *Interview progress (quick version): groups 1–4 done. Next: two last questions.*

## Saving progress

After every group, write the answers so far into `PROJECT_BRIEF.md` in the project folder, using the brief template. Put this line at the very top, in plain words, and keep it current:

> Interview progress: groups 1–3 of 8 done. Next: what it connects to.

The progress line sits directly under the title, where the template has "Confirmed by …". If the last group was answered but not yet said back and confirmed, say so: *Interview progress: groups 1–2 confirmed; group 3 answered, not yet confirmed.* Fields not yet asked read "Not answered yet". When resuming, read this file first, say where you are, read back any group that was not confirmed, and continue. When the owner confirms, replace the progress line with "Confirmed by <owner> on <YYYY-MM-DD>."
