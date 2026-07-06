# Spec: <title>

spec-version: <YYYY-MM-DD>.1
owner: <user> (Desired State is user-editable only; agents append to Status)
state: <authoring | reconciling | awaiting acceptance | accepted>
tier: <lite | full>

## Intent

<Why this exists, 1-3 sentences. Unverifiable wishes live here, not in Desired State.>

## Desired State
<!-- Rules: every line starts with "Ensure", every line observable, agents NEVER edit this section. -->

1. Ensure <observable outcome>.
2. Ensure <observable outcome>.

## Acceptance Checks
<!-- One row per criterion minimum. class: readiness (proves the feature; at least one required) | guard (existing behavior must not break) | guardrail (metric with threshold + baseline; never gates alone). observes: effective (running reality) | written (file contents — never sole evidence). tier: cheap (every loop) | expensive (pre-handoff). unknown verdicts REQUIRE a reason. -->

| # | Criterion | Check (command or concrete procedure) | class | observes | tier |
|---|---|---|---|---|---|
| 1 | | | readiness | effective | cheap |

## Non-goals & Ownership

- Non-goals: <explicitly out of scope>
- Do not touch: <surfaces owned by others / in flight>
- File owners: <artifact → single writer>

## Acceptance Protocol (user)
<!-- Generated from the ensure-list. 5-15 minutes, honestly estimated. -->

1. Run/click: <2-4 concrete steps>
2. Read (risk-ranked): <1-3 hunks, hardest-to-trust first>
3. Good looks like: <observable description>

## Status
<!-- Append-only, milestone-only, written AFTER acting and re-observing. Format: - <date> (spec-version <v>): <fact> — evidence: <pointer> -->

- <date> (spec-version <v>): spec authored. Awaiting execution.

## Teardown

- <processes to kill, scratch to remove>; archive this spec to specs/done/ on acceptance; follow-ups: <list or none>.
