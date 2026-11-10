# Working in chat (no folder on the person's computer)

Use this when you can't see a project folder you can save to (the Claude website, or Chat in the desktop app) and the person has chosen to work here rather than switch to Cowork. `get-ready` offers that choice. The method is the same; only where the files live and how they are saved changes.

## Where the files live

- **In a Claude Project** named after the project (recommended). The person adds the project's files to the Project's files, and every conversation in that Project can read them. You can read them but not change them: the person replaces them when you hand over new versions.
- **Without a Project:** the person keeps the files on their computer and attaches them at the start of each conversation. Say once that a Project saves them that step.
- **Your working copy:** at the start of a conversation, copy every project file you were given into one folder you can write to (your outputs folder, often `/mnt/user-data/outputs/<project name>/`). Work only on that copy. It disappears when the conversation ends, so what the person keeps is the only lasting copy. Say that once, plainly.

Name every file exactly as a folder project would (`PROJECT_BRIEF.md`, `CLAUDE.md`, `PLAN.md`, `BUILD_LOG.md` …), so the project can move to Cowork later unchanged.

## Handing files over

- **At every pause where a file changed** (the end of the interview, after the package is written, after each story, and before the person stops), share the changed files for download, with the tool that presents files to the person, and say exactly what to do: *"Replace BUILD_LOG.md and PLAN.md in your Project's files: delete the old ones and add these."* Name only the files that changed. `BUILD_LOG.md` changes whenever a step finishes.
- **The first time,** also say how: in the Project, open its files (the Project's knowledge, *check in your app*), and add or replace them there.
- **Before they stop,** make sure they have the latest files: *"Before you go, save these."* A step isn't safely finished until they have.
- Never hand over a file that holds a key, a password or personal details someone shouldn't see.

## Starting each conversation (the quick check in chat)

1. **Find the project's files:** in the Project's files, or attached to the message. If there are none, ask whether they have them; if this is a new project, start with `start-project-method`.
2. **Check they are the latest:** read the last entry of `BUILD_LOG.md` and say it in one line: *"The last step I see is Story 1.2, complete, on 2026-11-02. Is that the latest?"* If not, ask them to add the newer files before going on. (In the interview, the brief's progress line plays the same part.)
3. Copy them into your working copy, and carry on with the skill that called you.

## The interview in chat

Progress stays in the conversation while it lasts. If the person stops before confirming, hand over `PROJECT_BRIEF.md` with its progress line; to resume, they add it (to the Project, or attached) and say "continue my project". When the brief is confirmed, hand it over before generating the package.

## What works in chat, and what needs Cowork

- **Works here:** the interview, the brief and the plan; documents, guides and checklists; analysis of files they upload (you can run code on them here); a single-page tool or report to download; a page a team can open and use, which Claude refreshes when asked (for Wheelhouse data, the pack guide's §2); reading Wheelhouse data through Claude's Wheelhouse connector, and anything else through a connector, with the same yes before every real change.
- **Needs Cowork** (the desktop app, with a folder; or Claude Code for software): a scheduled refresh, where Claude updates a page or report on a schedule with nobody asking (the computer must be on); software that runs without Claude, on a server or their own website (`references/shape.md`, tiers 2 and 3); anything that needs an API key, because the key must sit in a private file on their computer, never in the chat or a Project's files; snapshots.
- **When the interview shows it needs Cowork,** say so once at the read-back, plainly, and offer: plan it here now, then move to Cowork to build. Don't stop them planning.
- **Moving to Cowork:** make a folder for the project, put every file in it, open it in Cowork (`get-ready` has the steps and the picture), and say "Where are we?". Nothing else changes.

## What stays the same

Everything else: plain words, every pause and review gate, the safety rules, the log is append-only, one story at a time, honest reporting.

- **Checks:** where a skill runs a helper script, run it on your working copy; in chat the scripts are in the skill's own folder.
- **Snapshots:** there are none in chat. The files the person keeps are the record; in place of the snapshot step, hand over the files.
- **Private details:** a Project's files are stored in the person's Claude account. Never put door codes, guests' contact details or keys in them, just as never in the chat.
