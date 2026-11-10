# Project Method

A Claude plugin that helps you define and build a project, even if you have never built anything before. It works for software (apps, websites, tools), data and analysis (figures that answer a question), and other projects such as guides, reports, documents and simple automations.

## What it does

1. **Asks you about your idea**, in plain words, a few questions at a time: what it is, who it is for, what is in and out, what it connects to, and what must never go wrong. "I don't know" is a fine answer. You can stop and pick it up later.
2. **Writes your project's plan**: a one-page brief you confirm, the rules Claude will follow, the plan broken into small steps, and a log that keeps every session on track. You see an outline and say yes before the details are written.
3. **Builds it with you, one step at a time.** Claude tells you what it is about to do, does it, checks it, and stops to show you at the points the plan marks with ★. It always asks before anything that sends, publishes, deletes, pays or changes real information, and the first time it does any of those, it does it for just one before everyone.

## Get started

1. **Install it.** In Claude (the desktop app or the website), open **Customize → Plugins → Add → Add marketplace** *(button names can vary)*, type `pricemethod/wheelhouse-plugin`, and install **Project Method**. (In Claude Code: `/plugin marketplace add pricemethod/wheelhouse-plugin`, then `/plugin install project-method@wheelhouse-plugin`.)
2. **Say "Start Project Method"** (or pick **+ → Plugins → Wheelhouse Project Method → start-project-method**).
3. **Choose where to work when Claude asks:**
   - **Cowork** (desktop app): click **+ New** at the top of the left sidebar, choose **Cowork** at the bottom left of the message box (it only shows on that start screen, not inside a chat), and connect a folder for your project. Claude saves everything there.
   - **Right there in chat** (website or app): keep the project in a **Claude Project**. Claude hands you the files as you go and you add them to the Project.

That's all. Claude takes it from there and then asks about your idea. You need a paid Claude plan (Pro, Max, Team or Enterprise); Cowork also needs the desktop app on a Mac or Windows computer.

## Who it's for

Best for something you'll keep using or build on: a tool for your team, a regular report, a guide you'll update. For a small, one-time thing, Claude offers a quick version: about ten questions and a short plan.

Your answers also decide what the finished thing is and where it's built, whatever it connects to:
- **Anywhere, the website included:** answers and reports from Claude when you ask, finished documents, and pages your team opens that Claude refreshes when you ask.
- **The desktop app (Cowork):** the same, refreshed by Claude on a schedule (your computer needs to be on).
- **Cowork or Claude Code:** software that runs without Claude, such as a website, an app or a script, with Claude as your developer.

Claude says why it suggests one and you decide. If a later idea needs a bigger one, Claude stops and asks rather than forcing it.

## Before you start

- **Two ways to work.** Your project is a few files (the plan, the rules, a log of what's done) that Claude rereads every session, so you can stop and pick up days later.
  - **Cowork, in the Claude desktop app** (or Claude Code): Claude saves the files in a folder on your computer for you. Works for everything.
  - **In chat, on the website or in the app, with a Claude Project:** Claude hands you the files as you go and you add them to the Project. Good for plans, documents, reports and analyses, and for a page your team can use that Claude refreshes when you ask. A scheduled refresh, software that runs without Claude, and anything needing an API key need Cowork; you can plan in chat and move later.
  Claude asks which you'd like at the start.
- **In Cowork, a folder just for this project.** Claude helps you make or pick one at the start (inside your Documents is a good place).
- **Have handy:** your idea in a sentence, who makes the decisions, and any deadline. Files you already have can be copied in later. You need no passwords and nothing to install.

Claude checks all of this with you at the start, in plain words, before any questions about your idea.

## What to say

To begin, *"Start Project Method"*, or choose **start-project-method** from **+ → Plugins → Wheelhouse Project Method** (or just tell Claude what you want to make). Later:
- *"Where are we?"* to pick up in any session;
- *"What's next?"* to build the next step;
- *"Let me review"* to stop and look;
- *"I want to add…"* for a new idea;
- *"I want to change the brief"* to change what the project is.

You never have to edit the files yourself. When the plan needs to change, Claude explains the change and makes it once you say yes.

## What you will see in your folder

`START-HERE.md` (read this first) and `PROJECT_BRIEF.md` are for you. `CLAUDE.md`, `PLAN.md`, `BUILD_LOG.md`, and any `GUIDE-*.md`, `FEATURE_MAP.md` (software projects: what is built and where) or `SAFETY.md` are Claude's working files; you can open them any time, but you never need to.

## Good to know

- **Privacy:** never paste passwords, keys or codes into the chat. If something needs one, Claude tells you where to put it. Personal details in your files (names, phone numbers, door codes) are kept out of the chat and the log.
- **Your Wheelhouse data:** if your project uses it, Claude brings what it needs to know about Wheelhouse (where to look things up, how to connect, what surprises people), reads before it changes anything, asks you before every change, and tries each kind of change on one listing first. How it gets your data follows your answers: Claude can read it when you ask, or build a page your team uses that it refreshes when you say so (teammates don't need to connect Wheelhouse), with nothing to set up. Something that must refresh on a schedule with nobody asking needs an API key. Never type your Wheelhouse password or API key into the chat.
- **Other systems too:** a project can use Wheelhouse together with other tools you use (for example your property management system), or have nothing to do with Wheelhouse at all. Claude checks each system's own instructions, only reads from it until it's clear what it holds, and, when two systems hold the same properties, checks they line up before building on them.
- **Honesty:** Claude tells you what it checked and what it did not.
- Some steps use small helper scripts that only read your project's files; Claude tells you before it runs one.

*Version 0.3.2.*
