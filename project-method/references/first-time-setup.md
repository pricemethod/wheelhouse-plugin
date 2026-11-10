# First-time setup (for Claude to walk someone through)

Use this when someone has never used Cowork or Claude Code. **The person never needs to read this file:** take them through it one step at a time, in these words, waiting after each step. Skip any step they have clearly done. Where a step says *(check in your app)*, button names vary between versions of the app: say so rather than inventing a name.

The same steps are in the launch video, the README in the Wheelhouse plugin repository and the Wheelhouse help page, so the person may have done some already.

## 1. What you need

- **A paid Claude plan:** Pro, Max, Team or Enterprise. (Cowork and plugins are not on the free plan.)
- **A Mac or a Windows computer** (Windows 10, version 2004 or newer). The phone app can't keep your project's files, so this needs a computer.
- **If you use Claude through work** (a Team or Enterprise plan), your administrator may need to allow plugins. You'll know at step 3.
- **Nothing else.** You don't need to install anything else or know any code.

## 2. The Claude desktop app

1. Go to **claude.com/download** and download the app for your computer.
2. Open it and sign in with your Claude account (the same one you use on the website).
3. If you already have the app, make sure it is up to date (many first-time problems are fixed in newer versions).

## 3. Add Project Method

1. In the Claude app, choose **Cowork**, then open **Customize** (left sidebar), then **Plugins**.
2. Choose **Add**, then **Add marketplace** *(check in your app: some versions show a "+" and "Add marketplace from GitHub")*.
3. Type **pricemethod/wheelhouse-plugin** and confirm. This is Wheelhouse's plugin library; if you added it before for other Wheelhouse plugins, it is already there.
4. Find **Project Method** in the list and install it. Make sure it is switched on.

**If you don't see "Add marketplace"**, or you see "Skills must be enabled in order to use plugins": your administrator has turned plugins off for your organization. Ask them to allow skills and plugins (Organization settings, then Plugins & skills).

**Updates** arrive on their own if **Sync automatically** is on for the marketplace; otherwise use **Check for updates** *(check in your app)*.

## 4. A folder for your project

Why a folder: Your project is a small set of files that Claude writes and then rereads at the start of every session: the plan, the rules it follows, and a log of what is done. That's what lets you stop and pick up days later without starting over. A plain chat or a Claude Project can hold files you upload, but Claude can't save and update its own files there, so it would lose track between conversations. A folder on your computer keeps them, and they stay yours.

Make a **new, empty folder** just for this project, named after it (for example "Guest Welcome Guide"). Inside your **Documents** folder is a good place. Don't use your whole Desktop, Documents or Downloads folder.

## 5. A Cowork session in that folder

*(Claude: show `skills/get-ready/cowork-switch.png` with this step if you can share an image here; it marks + New, the switch and the +.)*

1. Click **+ New** at the top of the left sidebar. This opens the start screen. (Important: the switch between **Chat** and **Cowork** is only on the start screen, never inside a conversation. If you are in a chat, you won't see it until you click + New.)
2. In the message box, at the bottom left next to the **+**, choose **Cowork** instead of **Chat**.
3. Connect your project folder, so Claude can read and save files there: use the **+** in the message box and choose the folder *(check in your app)*. If you haven't made the folder yet, the folder window has a **New Folder** button, so you can make it right there.
4. The first time, you may see **"Setting up Claude's workspace"**. That's normal; wait for it to finish.
5. On a Mac, your computer may ask whether Claude may use files in that folder. Choose **Allow**. If you clicked Don't Allow by mistake: **System Settings**, then **Privacy & Security**, then **Files and Folders**, find **Claude**, and turn access back on *(check on your Mac)*.

## 6. Say "Start Project Method"

Claude starts with a short setup check (it confirms it can keep files in your folder and asks your permission to create them), then asks about your idea, a few questions at a time.

## 7. When Claude or your app asks permission

- Claude asks before it creates or changes files, and before anything that sends, publishes, deletes or pays. Your app may also show its own **Allow / Deny** box. That's normal.
- **Allow** what you understand and expect (for example, creating files in your project folder).
- **Deny** anything you don't understand, and ask Claude in plain words what it is for.
- If your app offers a choice of how often to ask (for example **Manual**, **Auto**), choose the one that asks you every time (**Manual**) while you're new.
- Never paste a password, key or code into the chat. Claude will never ask you to.

## 8. Coming back another day

Open the Claude app, start a Cowork session in the **same folder**, and say **"Where are we?"**. Claude reads your project's files and tells you what is done, what is next, and anything waiting for you.

## If something goes wrong

| What they see | What to tell them |
|---|---|
| Claude says it can't keep files, or can't see a folder | You're in Chat, or no folder is connected. Click **+ New**, choose **Cowork** at the bottom left of the message box, and connect your project folder (step 5). |
| Can't find Cowork | It only shows on the start screen: click **+ New** first, then look at the bottom left of the message box, next to **Chat**. Still not there: you may be on the website or phone (use the desktop app), the app may need updating, or on a work plan your administrator may have turned Cowork off. |
| "Failed to start Claude's workspace", or it stays on "Setting up…" | Update the app to the newest version. On Windows, restart your computer and try again. |
| Project Method doesn't seem to be there | Check it's installed and switched on (step 3), then start a **new** conversation; plugins load at the start. |
| No "Add marketplace", or "Skills must be enabled…" | Your administrator needs to allow plugins (step 3). |
| Your Mac won't let Claude use the folder | Allow access in System Settings (step 5). |
| Not sure where you got to | Open the same folder in Cowork and say "Where are we?". |

---

*Claude Code instead of Cowork (for technical users):* install Claude Code (Mac: `curl -fsSL https://claude.ai/install.sh | bash`; Windows PowerShell: `irm https://claude.ai/install.ps1 | iex`), then in Claude Code run `/plugin marketplace add pricemethod/wheelhouse-plugin` and `/plugin install project-method@wheelhouse-plugin`. Start it from your project folder, accept the folder-trust prompt, keep the default (manual) permission mode, and say "Start Project Method".
