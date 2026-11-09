# Templates

The files `generate-package` writes into a user's project. One set of templates serves three project types (`software`, `data-analysis`, `other`) and three sizes (`lite`, `standard`, `full`); conditional blocks inside each file switch the type- and size-specific parts.

| Folder or file | What it is |
|---|---|
| `manifest.json` | The machine-readable map: every placeholder and what it means, every template, which types and sizes it applies to, and which placeholders it uses. |
| `START-HERE.md`, `PROJECT_BRIEF.md`, `CLAUDE.md`, `PLAN.md`, `BUILD_LOG.md` | In every package. |
| `GUIDE-glossary.md`, `GUIDE-design.md`, `GUIDE-reference.md`, `GUIDE-house-style.md` | The guides, for Standard and Full packages, by project type. |
| `SAFETY.md` | For Standard and Full packages whose project can change something real. |
| `FEATURE_PLAN.md` | Not in the first package; created by `add-feature` when the first new idea arrives. |
| `parts/` | Text that appears in several files, written once and included (house rules, review gates, story format, log format, the three "how we check" sections). |
| `examples/` | One worked example per project type: complete stories to use as a model. |

## Syntax

`{{name}}` is filled from the brief. Comments mark the rest, and a template stays readable as plain text:

- `<!-- include: parts/x.md -->` inserts that file here.
- `<!-- if: type=software; size=standard,full -->` … `<!-- /if -->` keeps the block only if every condition matches. Conditions are `type`, `size` and `safety` (`yes` when the project can change something real). Blocks nest.
- `<!-- note: … -->` is guidance for whoever generates the file and never reaches the user.
- `<!-- example: … -->` is a worked example for the generator and never reaches the user.

The generator must leave no `{{…}}` and no comment markers in a delivered file, and must fill every placeholder with the user's real answer (or "None", never a blank).
