---
name: downscope
description: Critique the current plan, spec, ticket breakdown, or implementation for scope bloat and propose the smaller version. Invoke whenever things feel bigger than they should be.
disable-model-invocation: true
---

# Downscope

Look at whatever is currently proposed in this conversation and shrink it.
Models default to doing too much; this skill is the counterweight, invoked at the moment it matters.

Judge everything against the pointed size from the Engineering Context if one was established (see the pre-flight skill).
"We agreed this is a 2-pointer and this plan reads like an 8" is a finding.

## What to look for, by stage

Apply the sections that match what is on the table right now.

**Spec or plan under discussion:**

- Restate the smallest version that still solves the stated problem.
- Move everything beyond it to an explicit "Later" list. Later is not a euphemism for "sneak it in".
- Flag requirements no one asked for and error handling for conditions the deployment context makes impossible.

**Ticket breakdown under discussion:**

- Flag any ticket with more than one behavioral outcome, or that mixes refactoring with behavior change, and propose the split.
- Flag any ticket whose review would be a heavy sitting: many layers, a migration plus a feature, or code a reviewer would have to reverse-engineer.
- Judge size by behaviors, layers, migrations, and review cost, not line counts. A mechanical change touching many files can be fine; a small auth or data-integrity change can still deserve its own ticket.

**Implementation or test plan under discussion:**

- Flag fallbacks nobody asked for, backward-compatibility shims the spec does not require, abstractions with one caller, and speculative configuration.
- Flag tests beyond the agreed seams or disproportionate to the pointed size.
- Flag polish beyond the acceptance criteria. Done means done.

## Output

Present a numbered **cut list**: each item is one concrete cut or split, with a one-line reason.
Walk it with the user item by item, grilling-style: recommend, then wait for their call.
Apply only what they approve. Do not silently rewrite anything.
