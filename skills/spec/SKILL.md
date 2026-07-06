---
name: spec
description: Author and reconcile durable, reconciler-style task specs (ensure-statements, executable acceptance checks, version stamps, acceptance protocol). Use when /work routes a lite/full task here, when asked to "write a spec", or to reconcile an existing specs/<slug>.md against reality.
argument-hint: "[author <ask> | reconcile <slug>]"
---

# spec — durable desired state, fresh observation, verified acceptance

A spec is a Kubernetes-style object: `Desired State` is the setpoint, `Status` is the measured variable, and any fresh session must be able to reconstruct the world from the file plus fresh observation alone. Format skeleton: [references/template.md](references/template.md). Test-first execution guidance: [references/tdd/GUIDE.md](references/tdd/GUIDE.md).

## Non-negotiable rules (both modes)

1. **Agents never edit Desired State.** Only the user changes intent (bumping `spec-version`). If reality proves a criterion wrong, propose the edit and stop — do not make it.
2. **Acceptance evidence observes effective state** — the rendered page, the running process, the real request — never file contents alone. Each check declares `effective` or `written`; written-only checks cannot be a criterion's sole evidence.
3. **Status is facts, written last.** Append only after acting and re-observing. Milestone-only: a criterion flipped, a blocker hit, work parked, handoff. Every entry stamped with the spec-version it reflects plus an evidence pointer.
4. **Unknown needs a reason.** A check may report `unknown` only with why it was unverifiable ("CI runs only on the PR itself"). "Didn't run it" is a fail, not an unknown.
5. **Optimistic concurrency.** Before any publishing write (commit/push/PR): re-observe — rebase, re-run the cheap tier. If `spec-version` changed since your snapshot, stop and re-plan; all prior Status is suspect (`observedGeneration` rule).

## Author mode

1. Input: interview output or the ask itself. If material decisions are unresolved, send it back through `interview` first.
1b. **Derive the bar when the user can't state it.** Start from intent: *"what would a user do to confirm this works?"* — that answer, made executable, is a readiness criterion. Classify every criterion you write:
   - **readiness** — user-observable behavior proving the feature does its job (the only class that can gate handoff);
   - **regression guard** — existing behavior that must not break (tests stay green, key routes still render);
   - **guardrail** — a metric with an explicit threshold AND baseline ("LCP ≤ production +10%", never bare "faster LCP"). Guardrails and regression guards support a spec but can NEVER be its only criteria — a spec with no readiness criterion is not authorable; go back to intent.
   Three bar patterns to propose when the user is unsure: **parity** ("matches production/reference, verified by <tool>"), **baseline-relative** ("no worse than current on <checks>"), **story-based** ("a user completes <flow> end to end in a real browser"). If the bar is still unclear, present 2-3 candidate bars via AskUserQuestion with previews — each option showing the concrete check list it implies — and let the user pick the bar rather than invent criteria for them.
2. Write `specs/<slug>.md` from the template. Authoring discipline:
   - Every Desired State line starts with **"Ensure"** and is observable — if you can't name its check, rewrite it or demote it to Intent.
   - Every criterion gets a row in Acceptance Checks: executable command or concrete browser procedure, `effective|written` flag, `cheap|expensive` tier.
   - Ownership names file-level owners and do-not-touch surfaces (one writer per artifact).
   - The Acceptance Protocol is generated FROM the ensure-list: 2-4 things to run/click, the 1-3 highest-risk hunks to read, what good looks like. 5-15 minutes of the user's time, honestly estimated.
   - **Lite tier**: same file, same eight sections, each may be a single line. Never omit Acceptance Checks or Acceptance Protocol.
3. Run `scripts/validate-spec.sh specs/<slug>.md`; fix violations before presenting.
4. Last line of your output, always: `Resume with: /work <slug>`

## Reconcile mode

1. **Gather once, at the top**: read the whole spec, `git status`/log, run the cheap check tier, read the last Status entries. No acting before the snapshot is complete.
2. **Distrust stale status**: if any Status entry predates the current `spec-version`, previously-passing criteria are unverified — re-observe them.
3. **Compute the gap**: for each ensure-statement, compare desired vs observed → converged / gap / unknown.
4. **Act idempotently**: close one gap at a time with re-runnable steps ("ensure X" semantics — safe to repeat). Same obstacle twice → record the blocker in Status and park; never hot-loop.
5. **Waiting on slow external state** (CI, deploys): record it, yield, and let the session end with the resume command — never poll hot.
6. **Publish** under rule 5 (rebase + cheap tier re-run first).
7. **Full tier only — independent refutation pass** before handoff: spawn a fresh-context subagent given ONLY the spec's Intent + Desired State + the diff (never your reasoning or the Status log), instructed: *"For each criterion, try to show it is NOT actually met — cite file:line or runtime evidence. Default to 'not proven' when uncertain."* Record per-criterion verdicts in the acceptance pack (`independently-verified` / `refuted → back to reconcile`). This must run on the harness itself — external review CLIs are an optional upgrade when present, never a dependency.
8. **Handoff**: run `scripts/validate-spec.sh`, assemble the acceptance pack (check table with verdicts + unknowns-with-reasons, the protocol, risk-ranked hunks), append the final Status entry, set state to **awaiting acceptance**. Majority of criteria must be `effective`-verified. Never mark anything done — acceptance is the user's.
9. **Teardown on acceptance**: execute the spec's Teardown section (kill dev servers, remove scratch, archive spec to `specs/done/`, note follow-ups).
