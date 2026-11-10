---
name: get-ready
description: "Checks that a person is set up to run a project before anything starts, in plain words: that Claude is working in a folder on their computer (Cowork or Claude Code), or, if not, offering to work in chat with the files kept in a Claude Project; that the folder is a good one for a project, that Claude may create files there, and what to have handy. Use first when someone says 'Start Project Method' (the phrase in the launch video and the README) or otherwise starts a new project (before the `start-project-method` skill), when someone asks 'what do I need', 'how do I set this up', 'is this the right place', or 'before we start', and as a quick check at the start of every later session (next-story, where-are-we, add-feature). Never installs anything and never asks for a password."
---

# get-ready

**Where the plugin's files are:** the `references`, `templates`, `packs` and `scripts` folders named below are in the plugin's folder, two folders up from this file. In Claude's chat only this skill's own folder is loaded, so the files this skill needs are also copied into it, in folders of the same names next to this file. Use whichever exists.

Before a project starts, make sure the person is set up to finish it. Most of the people using this are not technical, and many will never have used Cowork or Claude Code before, so a missing folder or a wrong place discovered halfway through would cost them their work. Do this kindly, briefly, and one thing at a time. The plain-language guide is `references/setup.md`; use its wording. The step-by-step guide for someone using Claude this way for the first time is `references/first-time-setup.md`; follow its steps and wording. The person should never need to find or read either file: you carry them through it.

There are two versions: the **full check** before a new project, and the **quick check** at the start of every later session.

## The full check (new project)

0. **Welcome,** when this is the person's first message (for example "Start Project Method"): two short lines at most. "Welcome to Project Method. I'll ask about your idea, write it up as a plan you approve, then build it with you one step at a time. First, a quick check that you're set up." Then go straight to step 1. Do not list the skills or explain the method further; the person learns it by doing it.
1. **Can I keep files on their computer?** Find out whether you are working in a folder on the person's computer where files you create will still be there next time (Cowork or Claude Code). If you cannot see such a folder, this is a plain chat or the phone app: say so in plain words (the "Say it like this" line in `references/setup.md`, which says why: the plan, rules and log are files you write and reread every session, and a chat or a Claude Project can't hold files you update), then **ask one question first: are they in the Claude desktop app or on the website?** You can't tell from here (Chat looks the same to you in both), so never guess or say "I see you're using…". If something in this conversation shows for certain which app it is, use that and skip the question. Then **offer the two ways to work**, with the reasons that fit their answer, and wait for their choice:
   - **Desktop app:** recommend Cowork: *"Cowork is the best place for this: it saves your plan, rules and log for you, so you pick up exactly where you left off, and it can build things that run on your computer."* Show the picture and the steps (below). Mention the chat way in one line, for anyone who'd rather stay.
   - **Website:** ask whether they have the desktop app installed. *"If so, Cowork there is best: it saves your project's files for you and can build things that run on your computer. If not, no problem: we can work right here. I'll hand you the files as we go, and you keep them in a Claude Project."* If they have it, show the picture and the steps; if not, the chat way.
   - **Not sure:** *"On a new chat, if you see Chat and Cowork at the bottom left of the message box, you're in the desktop app."*

   The two ways, for reference:
   - **Cowork** (the desktop app on a Mac or Windows computer): their files are saved for them in a folder. Best for anything, and needed for a scheduled refresh, software that runs without Claude, or an API key.
   - **Right here, in a Claude Project** (works on the website too): you hand them the project's files as you go and they add them to the Project. Good for plans, documents, reports and analyses; something that has to run on their computer can move to Cowork later.

   **If they choose Cowork,** give the switch as numbered steps. The one thing people miss is that the switch between Chat and Cowork is only on the start screen, never inside a conversation:
     1. Click **+ New** at the top of the left sidebar (this opens the start screen).
     2. In the message box, choose **Cowork** at the bottom left, next to **Chat**.
     3. Connect a folder just for this project with the **+** in the message box; the folder window has a **New Folder** button if they need one.
     4. Say "Start Project Method" there. This chat can be closed after that.

     **Show the picture first, then the steps. Don't skip this because it looks optional:** people miss this switch even with the steps in front of them. The picture is `cowork-switch.png`, in this skill's own folder, right next to this file (it lives here because in Claude's chat only a skill's own folder is available); it marks + New, the Chat / Cowork switch and the + for the folder.
     - If you have a tool that presents or shares a file with the person (in Claude's chat it is usually called `present_files`, and it only shares files from the outputs folder, often `/mnt/user-data/outputs/`), copy the picture there and present it, then give the steps.
     - If you can show an image some other way in this conversation, do that.
     - Only if you have no way to show a file or image, give the steps alone. Never send a link to the picture instead.
   - **If they can't find Cowork:** say again that it only shows after **+ New**, on the start screen. If it still isn't there, they may be on the website or phone (they need the desktop app), the app may need updating, or on a work plan an administrator may have turned Cowork off. Offer the chat way instead, or continue as for a first-timer.
   - **If they want Cowork but don't have the desktop app, or say they're new to all this (a first-timer):** walk them through `references/first-time-setup.md` one step at a time, waiting after each. Project Method is already running, so skip what they have clearly done (they have a plan and the plugin); usually what is left is: the Claude desktop app on a Mac or Windows computer, signed in and up to date (if they are on the website or the phone); Project Method installed in that app too, if it is not there; a new folder for the project; a Cowork session with that folder connected (via **+ New**, then Cowork at the bottom left of the message box); "Setting up Claude's workspace" being normal; choosing Allow if their computer asks about the folder. Where the guide says *(check in your app)*, say so rather than inventing a button name. Then ask them to say "Start Project Method" in the new Cowork session, and stop here.
   - **If they choose to work here (chat):** follow `references/chat-mode.md` from now on, in every skill. If you can't tell whether this conversation is in a Claude Project, ask. If it isn't, offer to help them make one: **Projects** in the left sidebar, then a new project named after theirs, then a new chat inside it where they say "Start Project Method" again *(check in your app)*. If they'd rather not use a Project, carry on here; they keep the files and attach them each time. Then skip step 2 (there is no folder to check), and in step 3 ask instead: "I'll hand you the project's files to keep as we go. OK?" Skip step 4.
2. **Is it a good folder?** If you can run Python, say you will run a quick read-only check, then run `python3 -I <plugin folder>/scripts/setup_check.py <folder>` (the plugin's `scripts` folder is two folders up from this skill). Otherwise look yourself. Then:
   - **A problem** (not writable, the whole home, Desktop, Documents or Downloads folder, a file rather than a folder): explain it in one sentence and ask them to make or choose a folder just for this project. Wait.
   - **Other files in it:** say a project works best in its own folder, and ask whether to go on here or use a new one.
   - **Already has a project:** this is not a new project. Hand over to `where-are-we`.
   - **An interview in progress:** hand over to `start-project-method`, which resumes it.
   - **Cloud-synced:** mention it is fine, and to avoid working from two computers at once.
3. **May I create files here?** Ask once, in one line, naming the folder and saying why: "I'll keep your project's files in <folder> (the plan, the rules and a log, so we can pick up where we left off). OK to create them there?" Wait for a yes.
4. **Permission boxes:** say in one line that their app may also show its own Allow / Deny boxes when you create files; that is normal; allow what they understand, and ask you about anything they don't. If the app offers a choice of how often to ask, suggest the one that asks every time while they are new.
5. **What to expect, in five short lines at most:** about 17 short questions, a few at a time, each with an example (a quicker version of about 10 for a small, one-time thing); "I don't know" is a fine answer, and they can stop any time and pick up where they left off; at the end they get a one-page summary of the project to check, then a step-by-step plan; have the idea, who decides and any deadline handy; no passwords or keys, and nothing to install. Don't give a time in minutes: it hasn't been measured, and a number up front puts people off. Ask whether they are ready to begin.
6. **Hand over** to `start-project-method`.

## The quick check (every later session)

Silently confirm you are in the project's folder and can save files there (and, if you can run Python, that `setup_check.py` reports no problem). If all is well, say nothing about it and carry on with the skill that called you. If not, stop and explain in one or two plain sentences what is wrong and how to fix it (most often: "Please open this project's folder in a Cowork session; I can't see it from here. Click + New, choose Cowork at the bottom left of the message box, and connect the folder.").

**In chat** (the project works in a Claude Project, or the person attaches its files; `references/chat-mode.md`): the quick check is "Starting each conversation" in that guide: find the project's files, confirm with the person that the last log entry is the latest, and copy them into your working copy. Don't send them to Cowork unless the next step needs it.

## Rules

- **Never install anything,** and never ask the person to install something you have not explained and they have not agreed to. (Setting up the Claude desktop app is the person's own step, from the official download page; you only explain it.)
- **Never suggest a setting that skips permission prompts.** While someone is new, the one that asks every time is right.
- **Never ask for a password, key or token.** None are needed to start.
- **Never create files before they have said yes** to the folder.
- **Plain words, short messages, one question at a time.** This is the first thing the person sees; make it feel easy.
- If something cannot be checked (for example, Python is not available), say what you will do instead (check by reading the files) and carry on.

## What not to do

- Do not start the interview before the folder is settled.
- Do not use a folder with problems because the person is in a hurry; explain why it matters (their work would be lost or mixed with other files) and offer the quick fix.
- Do not repeat the full check in later sessions; use the quick check.
