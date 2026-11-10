# Packs

A *pack* adds knowledge about one outside system to the method without changing the core: where to look things up, what surprises people, extra safety rules, and ready-made early stories. The core never depends on a pack; a project that doesn't use the system never loads it.

## What switches a pack on

The brief's **Systems and accounts** line (see `references/scope.md`). When it names a system that has a pack here, every skill that touches that system reads the pack's `README.md` first and follows it. A system with no pack is covered by `references/other-systems.md`.

## The shape of a pack

```
packs/<system>/
  README.md    when it switches on, what it adds, and which file to read when
  guide.md     where to look things up, and the facts and surprises, each checked against real data
  stories.md   the early stories the pack adds to a plan, in the house story format
```

A pack's rules sit on top of the core rules and never loosen them. Facts in a pack carry the date they were last checked; anything not checked says so.

## Packs here

| Pack | For |
|---|---|
| `wheelhouse/` | Projects that read or change the person's Wheelhouse data, through the Wheelhouse connector or the Wheelhouse RM API. |
