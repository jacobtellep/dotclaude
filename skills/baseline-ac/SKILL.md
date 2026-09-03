---
name: baseline-ac
description: Standing acceptance criteria for every spec and ticket. Use when writing or reviewing acceptance criteria, a spec, or a ticket breakdown; when checking a finished diff against them; or when scope grows mid-implementation — a fallback, a compatibility shim, a new dependency, a single-caller abstraction, or configuration nobody asked for.
---

# Baseline Acceptance Criteria

A standing guard list against scope bloat. These criteria go at the top of every spec's Acceptance Criteria section, before the feature-specific ones, and apply to every ticket generated from that spec.

Drop an item only when the **Engineering Context** explicitly makes it irrelevant, and say so in the spec. The Engineering Context is this skill's own output — see [`INTERVIEW.md`](INTERVIEW.md).

## The criteria

- [ ] No backward compatibility unless the spec explicitly requires it: old code is deleted, old callers break loudly
- [ ] No fallbacks or error handling for conditions the deployment context makes impossible
- [ ] No new dependencies unless the spec explicitly lists them
- [ ] No speculative abstractions, configuration, or hooks for needs the spec does not have
- [ ] No refactoring mixed into behavior changes unless inseparable, and then called out
- [ ] Tests exist only at the agreed seams and are proportionate to the pointed size
- [ ] Every non-obvious piece of code is traceable to a requirement in the spec
- [ ] Each ticket carries one behavioral outcome
- [ ] Each ticket is a light review: few layers, no migration bundled with a feature, nothing a reviewer must reverse-engineer

These are verification checkboxes, not instructions — each is asserted against a finished spec, ticket, or diff. Phrased as negatives on purpose: the check is that the named thing is absent.

Size is judged by behaviors, layers, migrations, and review cost — never line counts. A mechanical change touching many files can be fine; a small auth or data-integrity change can still deserve its own ticket.

## Where this runs

Five branches, one list.

**No Engineering Context yet, and a spec is coming.** Ask the user once whether to establish it, then follow [`INTERVIEW.md`](INTERVIEW.md). Never open the interview unasked.

**Spec authoring.** Prepend the criteria to the spec's Acceptance Criteria section, above the feature-specific ones. Name any criterion the Engineering Context dropped, and why.

**Ticket breakdown.** Apply the last two criteria (one behavioural outcome; light review) per ticket, and propose the split where one fails. Everything beyond the smallest version that solves the stated problem goes on an explicit **Later** list — Later is not a euphemism for sneaking it in.

**Finished diff.** Walk every criterion and report which hold and which break. Cite the specific code for each break.

**Scope growing mid-implementation.** When the work reaches for a fallback, a compatibility shim, a new dependency, a single-caller abstraction, or unasked-for configuration, name the criterion it crosses and get a decision before writing it.

## Pointing is the scope budget

The user's own size estimate is the anchor. Everything downstream is measured against it: a one-point ticket carrying an integration suite fails the proportionality criterion even when every test passes. "We agreed this is a 2-pointer and this plan reads like an 8" is a finding worth stating plainly.

## Maintaining this list

This is a growing list of failure modes worth guarding against by default. When a review or a shipped change reveals a new recurring failure mode, add it here rather than re-teaching it per ticket.
