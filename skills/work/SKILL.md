---
name: work
description: Front door for any task — sizes it, routes it, and guarantees verified acceptance. Use to start any nontrivial task ("/work <ask>"), to resume/continue/pick up parked work ("/work <spec-slug>", or when the user says "continue X", "resume the Y work", "pick up where we left off"), or bare "/work" to list unconverged specs in this repo.
argument-hint: "[task description | spec slug | (empty = list specs)]"
---

# /work — the gate

You are a thin gate. You size, route, and enforce — you never own stage logic. Interview owns intent, `spec` owns the format and the reconcile loop, `goal`/`checks`/`evidence` own execution and verification. If you find yourself implementing, stop and route.

## 0. No arguments → list

If invoked with no task and no slug: find `specs/*.md` in the repo (excluding `specs/done/`), print each slug with its `state:` line and last Status entry, and ask which to reconcile. If no `specs/` exists, say so and ask for a task.

## 1. Resolve the input

- Matches an existing `specs/<slug>.md` (or clearly refers to one — "continue the auth work") → invoke the `spec` skill in **reconcile mode** on that file. Done here.
- Otherwise it's a new ask → size it.

## 2. Size it — checklist, not judgment

State your call in exactly one line before anything else:
`Sizing: <none|lite|full> — <one-line reason>` (the user can override with a word).

**none** is allowed ONLY if ALL four hold:
1. Single file touched.
2. No shared or exported surface (nothing another module/site/package imports or renders).
3. One observable check proves it.
4. Reversible in one commit.

Anything borderline → **lite**. Multi-criteria, multi-session, shared code, or anything the user will want to verify in stages → **full**. When in doubt, size UP — a lite spec costs three lines; a missed shared-surface regression costs a day.

## 3. Route

- **Intent unclear or decisions unresolved** → run the `interview` skill first (it teaches when the user can't answer). Then continue below with its output.
- **none** → just do the task. The floor still holds: finish with `/checks` and the `evidence` block. No file.
- **lite / full** → invoke the `spec` skill in **author mode** (pass the interview output or the ask). Then execute against the spec: use goal mode if available for the implementation phase, run the spec's cheap checks each loop, and follow the `spec` skill's reconcile rules (gather first, idempotent steps, status written last).

## 4. Enforce the handoff bar

Before reporting work as ready:
- **none** → evidence block present, or it is not done.
- **lite** → all acceptance checks run (pass/fail/unknown-with-reason) + evidence block.
- **full** → all of the above, majority of criteria verified against effective (running) state, AND the `spec` skill's **independent refutation pass** completed with verdicts recorded. No refutation pass, no handoff.

Terminal state is always **"awaiting Jake's acceptance"** — never "done". Deliver the acceptance pack (from the spec) or the evidence block (none-tier), and if work is parked, print the resume command: `/work <slug>`.
