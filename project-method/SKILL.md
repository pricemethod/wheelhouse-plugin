---
name: project-method
description: "A guided method for building any project with Claude: a plain-language interview turns an idea into a complete project package (rules, plan, stories, build log), then Claude builds it one reviewed story at a time. Works for software, data and analysis work, documents and automations."
metadata:
  version: "0.3.2"
  author:
    name: Wheelhouse
    email: support@usewheelhouse.com
  tags: project-planning,methodology,stories,build-log,guided-build
---

# Project Method — Agent Skills

A skill pack that carries a proven way of building: define the project first, write it down, build it in small reviewed steps, and keep a log so any session can pick up where the last one stopped. Prefer these skills over improvising a plan.

## Load order

0. **Setup first.** "Start Project Method" (the phrase clients are shown) always begins here. Before a new project, load `get-ready` (the full check: a folder on the person's computer, a good folder for the project, permission to create files, what to have handy; or, with no folder, the choice of Cowork or working in chat). At the start of every later session, its quick check runs first.
1. If `PROJECT_BRIEF.md` starts with "Interview progress", the interview is unfinished: load `start-project-method`, which resumes it.
2. If the folder has no `PROJECT_BRIEF.md`, this is a new project: load `get-ready`, then `start-project-method`.
3. If it has a confirmed brief but no `PLAN.md` or `BUILD_LOG.md`, load `generate-package`.
4. If it has a package (`CLAUDE.md`, `PLAN.md`, `BUILD_LOG.md`), load `where-are-we` first in a cold session, then `next-story` to build.
5. A new idea the owner wants becomes a feature with `add-feature`, at any stage. To correct what the project is (the brief), follow "Changing the brief" in `generate-package`. Use `review-gate` at every pause, and `story-writer` when a story is unclear or too big.

## Skills

| User intent | Skill | Description |
|---|---|---|
| Start Project Method. What do I need before I start? Is this the right place? | `get-ready` | Setup check: a folder on their computer, a good folder, permission, what to have handy |
| I have an idea and want to build it; help me plan this | `start-project-method` | Interview that produces the Project Brief |
| Turn my brief into a plan and files | `generate-package` | Generate the project package |
| What's next? Go. Keep going. | `next-story` | Build the next story, test it, log it, stop at gates |
| Let me review before you continue | `review-gate` | Pause with what exists, how to look, decisions needed |
| I want to add a feature; I have a new idea | `add-feature` | Append a feature plan, stop for review |
| Where are we? Catch me up. | `where-are-we` | Read-only status of the project |
| This story is unclear or too big | `story-writer` | Write or split a single story |

## House rules (apply to every skill)

- **Plain language.** Explain every term the first time. Never assume the user is technical.
- **Never skip a pause.** If a review gate cannot be shown, stop and say so.
- **Report honestly.** Failed tests and checks that were not run are named, never smoothed over.
- **Files are the memory.** Rely on the package files, not on recollection of an earlier conversation.
- **The user owns the plan.** Propose plan changes in the log and make them only after the owner says yes to that exact change. Never rewrite history.
- **Protect personal details** found in the project's files: never print them in the chat or the log.
- **No secrets in chat.** Tell the user where a key belongs; never ask them to paste one.
- **What the project connects to decides what extra knowledge applies** (`references/scope.md`): Wheelhouse data → `references/wheelhouse.md` and the Wheelhouse pack (`packs/wheelhouse/README.md`); any other system → `references/other-systems.md`; more than one together → `references/joining-systems.md`. Nothing extra for a project that connects to nothing.
- **The shape follows the answers** (`references/shape.md`): how the finished thing is used and kept up to date (tier 1, anywhere: with Claude when asked, a finished file, a page a team uses; tier 2, Cowork: Claude refreshes it on a schedule; tier 3, Cowork or Claude Code: software that runs without Claude) is chosen from the interview, written in the brief with the reason and what would change it, and checked again whenever something is added. Never switch shape, or carry on past a reason to, silently.
- **Two ways to work.** In a folder (Cowork or Claude Code), Claude saves the files itself. In chat (the website, or Chat in the desktop app), the files live in a Claude Project and Claude hands over every changed file at each pause (`references/chat-mode.md`). The method is the same; a scheduled refresh, software that runs without Claude, and API keys need a folder (`references/shape.md`).
- **Ask before outward-facing or irreversible actions** (sending, publishing, deleting, spending, writing to real data). An earlier yes does not carry to the next action.
