# Project Brief — {{project_name}}

Confirmed by {{owner_name}} on {{today}}.

This is the source for the plan; if something here changes, the plan is regenerated from it.

## The idea
{{one_liner}}

## Who decides
- **Owner (makes the decisions):** {{owner_name}}

## Type and size
- **Type of project:** {{project_type}}
- **Size of the plan:** {{size}}
- **Why this size:** {{size_reason}}
<!-- note: "Type of project" and "Size of the plan" are single exact words (software, data-analysis or other; lite, standard or full), because the plugin's helpers read them. The explanation goes in "Why this size". While the interview is in progress, the line "Confirmed by …" is replaced by the progress line, in the same place. -->

## Who it is for and what success looks like
- **Who will use it, or read it:** {{audience}}
- **What success looks like:** {{success_definition}}

## What is in, what is out, what is later
- **In scope (we are doing this):** {{in_scope}}
- **Out of scope (we are deliberately not doing this):** {{out_of_scope}}
- **Later ideas (parked, not forgotten):** {{later_ideas}}
<!-- note: write the in-scope items on one line, separated by semicolons, so the package checker can see that each one gets a story. -->

## What it connects to
- **Systems and accounts:** {{systems}}
- **Data and files it uses:** {{data_sources}}
- **Can it change anything real** (send, publish, delete, update data)? {{real_world_changes}}

## How it will be used and kept up to date
- **Shape:** {{shape}}
- **Why:** {{shape_reason}}
- **Check again if:** {{shape_switch_if}}
<!-- note: the shape is chosen from the answers, not from how technical the owner is. Claude checks "Check again if" every time something is added, and raises it as a decision when one is met. -->

## What must never happen
{{never_events}}

## Look, feel and words
{{look_and_feel}}
<!-- if: type=software -->
- **Devices it must work on:** {{devices}}
<!-- /if -->

## Constraints
{{constraints}}
- **Deadline:** {{deadline}}

## How we will work together
- **Pauses:** {{review_cadence}}
- **Saving snapshots (commits):** {{commit_policy}}
- **Comfort with technical detail:** {{comfort_level}}

## Open questions
Each of these gets answered early (in Story 0.2, or in a story of its own when later work depends on the answer), and the answer is recorded in the plan's decisions table.

{{open_items}}

## Key terms
{{key_terms}}

<!-- example: For an invented "Pace Watch" report, "Key terms" might list: pacing (bookings so far compared with the same point last year), ADR (average price per booked night), owner minimum. -->
