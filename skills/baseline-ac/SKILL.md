---
name: baseline-ac
description: Baseline acceptance criteria that apply to every spec and ticket by default. Use when writing, reviewing, or revising acceptance criteria, a spec, or a ticket breakdown — and when checking a finished diff against the criteria it was built under.
---

# Baseline Acceptance Criteria

A standing guard list against scope bloat. These criteria go at the top of every spec's Acceptance Criteria section, before the feature-specific ones, and apply to every ticket generated from that spec.

Drop an item only when the spec's Engineering Context explicitly makes it irrelevant, and say so in the spec.

## The criteria

- [ ] No backward compatibility unless the spec explicitly requires it: old code is deleted, old callers break loudly
- [ ] No fallbacks or error handling for conditions the deployment context makes impossible
- [ ] No new dependencies unless the spec explicitly lists them
- [ ] No speculative abstractions, configuration, or hooks for needs the spec does not have
- [ ] No refactoring mixed into behavior changes unless inseparable, and then called out
- [ ] Tests exist only at the agreed seams and are proportionate to the pointed size
- [ ] Every non-obvious piece of code is traceable to a requirement in the spec

These are verification checkboxes, not instructions — each one is asserted against a finished spec, ticket, or diff. Phrased as negatives on purpose: the check is that the named thing is absent.

## Where this runs

Three points, same list:

- **After a grilling session** — the plan exists but no spec does yet. Name the criteria the plan is now committed to, and flag any that the plan already violates.
- **After `/to-spec`** — prepend the criteria to the spec's Acceptance Criteria section, above the feature-specific ones.
- **Against a finished diff** — walk the list and report which criteria the diff satisfies and which it breaks.

## Pointing is the scope budget

The user's own size estimate for the work is the anchor. Test proportionality against it: a one-point ticket carrying an integration suite fails the tests criterion even when every test passes.

## Maintaining this list

This is a growing list of failure modes worth guarding against by default. When a review or a shipped change reveals a new recurring failure mode, add it here rather than re-teaching it per ticket.
