---
name: pr-description
description: Write a pull request description in the standard TASK/SOLUTION/Tester Notes format, with testing steps a human follows manually on the deploy preview. Use whenever a PR is being opened or its body edited — whether the user asked for the PR or you decided to open one yourself.
---

# PR Description

Applies to every `gh pr create`, `gh pr edit --body`, and any other write of a PR body.
Write the body to a file and pass `--body-file`; never inline a multi-line body in the shell.

If the repo has `.github/pull_request_template.md`, that file wins on section names and order. Follow it, and apply the rules below within it. The sections referenced here are the ones in the standard template.

## The one rule that matters

**Testing steps tell a reviewer how to exercise the change by hand on the deploy preview.** They are instructions, not a report.

Never write what you tested, what you ran, or what passed. No "verified X", no "all tests pass", no "confirmed on mobile", no test-run output, no summary of your own QA. The reviewer has not tested anything yet — the section exists so they can.

## Sections

**TASK** — one or two sentences on what is being implemented, updated, or fixed. Fill in the Asana link if a task URL is known; otherwise leave the empty link in place.

**SOLUTION** — short summary of the approach: what changed structurally, technical considerations, anything a reviewer would otherwise have to reverse-engineer from the diff (data sources, new libraries, migrations, config). Skip the file-by-file tour.

**Development & Review Checklist** — leave every box unchecked. These are human attestations; do not check them on someone's behalf, and do not check "All tests pass locally" even if they do.

**Tester Notes** — this is where the manual testing steps go. Leave the template's checkboxes unchecked, and replace the trailing comment with numbered steps.

**Previews** — the deploy preview URL, deep-linked to the affected pages or Storybook stories, not the site root. If the preview URL is not known yet, leave a placeholder line saying it will be added once the preview builds.

**Pre-Merge / Post-Merge** — real follow-ups only (stakeholder sign-off, content entry, env vars, cache purge, migration to run). Write "None" rather than inventing filler.

## Writing the testing steps

Numbered, imperative, each step something the reviewer clicks, types, or looks at. Start from the deploy preview URL and assume no context beyond the PR.

Cover, in order:

1. **Happy path** — the primary behavior the change exists to deliver.
2. **Edge cases and states** — empty, long, missing, error, loading, unauthenticated, whatever this change actually introduces.
3. **Viewports** — only where layout changed, and say which breakpoints matter and what should hold at each.
4. **Regression surface** — the neighboring pages or flows this change could plausibly break, named specifically.

Each step names where to go and what to expect. Include any fixture data, test account, query string, or CMS entry needed to reach the state — if a state cannot be reached on the preview, say so and say how to reach it instead.

Cut steps that verify nothing about this PR. Three sharp steps beat twelve generic ones.

### Shape

```markdown
### Tester Notes

_(Check = Yes; leave unchecked if No or incomplete)_

- [ ] Verified no regressions in related features or pages
- [ ] Confirmed responsive behavior works as expected
- [ ] Additional task-specific testing notes are included here and in Asana

**How to test:**

1. Open `<preview-url>/knowledge-hub`.
2. Type "grant" into the search field. Results should filter as you type, with the matched term highlighted.
3. Clear the field. The full unfiltered list should return without a page reload.
4. Search "zzzzz". An empty state should appear reading "No results found", with the Reset filters button.
5. At 375px wide, the filter panel should collapse into the "Filters" accordion above the results.
6. Visit `<preview-url>/events` — it shares the same list component and should be unchanged.
```

## Before opening the PR

Read the diff (`git diff <base>...HEAD`) so TASK and SOLUTION describe what actually changed, and so the testing steps point at real routes, real selectors, and real states. Do not describe intent you did not ship.
