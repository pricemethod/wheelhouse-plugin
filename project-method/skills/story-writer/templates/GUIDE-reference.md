# Guide: what {{project_name}} connects to

What this project reads from, what it might change, and what to watch out for. Checked against the real thing early (see the plan's first phase), then kept current.

## Systems and accounts
{{systems}}

## Data and files
{{data_sources}}

## Can it change anything real?
{{real_world_changes}}

## For each system or file, write down (verified, not assumed)
- **What it is called, who owns it, and where it comes from** (a live system, or a file someone hands over; how often a new copy arrives).
- **How access works,** and where the key or login is kept (a private file that is never shared or committed; never pasted into chat).
- **What shape the information comes in** (for a file: its columns and what each means), with one real example with private details removed.
- **Whether it holds personal details,** and how they are kept out of the chat, the log and snapshots.
- **Limits:** for a live system, how many requests per minute and how much at once; for a file, how big, how fresh, and what period it covers.
- **What goes wrong:** the errors seen so far and what each one means.
- **How to read it safely:** which requests only look, and which ones change things.

## Facts learned by trying it
*(Add each surprise with the date. Real systems often differ from their own documentation; what we saw is what counts.)*
