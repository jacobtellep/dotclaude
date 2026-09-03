# DatoCMS incidents and lessons

Dated, from Claude Code and Codex sessions. Each one is a rule in `SKILL.md`; this file is the reason behind it.

## Contents

- Near-misses on primary
- Destructive script defects caught in review
- Partial failures
- Wrong-environment wiring
- Lost tooling and false premises
- Scope and evidence failures

## Near-misses on primary

- **2026-05-13, kingshammer (Codex).** Adversarial review of the Constant Contact intake work found: the Form schema migration was primary-capable despite docs claiming otherwise; `npm run migrate` used the normal token with no explicit environment; `migrate-all.ts` read primary via HQ discovery before target verification; dry runs could reach primary after a sandbox promotion because they used ordinary tokens; `run-sandbox-migrations.ts` silently ignored `--dry-run` because argv was never parsed; credential introspection attested a different token than the caller used. Jake: "approve Dato seeding safety repairs. please do not touch the primary env. ever."
  Lesson: audit the whole write path, not the guard in isolation: the default-environment command, discovery calls that run before verification, the dry-run credential, and whether flags are even parsed.
- **2026-07-30, ample-co (Claude Code).** A spec review of the sandbox harness found unguarded exported CMA clients a future script could import to write anywhere, bypassing the CLI-level guard. Fixed before the first real write.
  Lesson: make the sandbox invariant structural; the write-client factory takes no environment argument.
- **2026-05-13, kingshammer.** Production submission handler honoured `DATOCMS_ENVIRONMENT_HQ` / `DATOCMS_ENVIRONMENT`, so production could read sandbox routing before writing real PII to Constant Contact.
  Lesson: production request paths omit every environment header and override.
- **2026-08-12, ample-co.** After the real promote, Netlify's `DATOCMS_ENVIRONMENT` was still pinned to `main` in every context. `main` was now the demoted environment with no `Post` model; the next production build would have failed on `allPosts`. Fix: unset it, since blank means primary.
  Lesson: a promote invalidates every hardcoded environment name; audit them as part of the promote runbook.

## Destructive script defects caught in review

- **2026-07-30, ample-co.** A page-removal script's first draft deleted `page` records on slug match alone; an ordinary page sharing a slug with a converted post would have vanished silently. Caught before it ran.
  Lesson: require two independent signals to agree before deleting, refuse the whole run on disagreement, and put destructive scripts through adversarial review before execution.
- **2026-07-29, ample-co.** A depth-probe script that writes schema leaked orphan item types when it threw mid-run; `migrate` created a ledger model even with zero migrations; a comment claimed dry runs write.
  Lesson: schema-creating scripts need discovery-based teardown that also cleans after a crash; a dry run must be provably write-free.
- **2026-03-13, kingshammer.** Pre-run review of `migrate-content-placement.ts` found `executeR2R3()` created and published a replacement carousel before reaching the "already migrated" skip branch, and `buildMutationPlan()` deduplicated shared rows by id, freezing a derived title from the first page while stripping heading rows from every referencing page.
  Lesson: shared records are the primary hazard; reject conflicting derived values and never destroy a record still referenced elsewhere.
- **2026-08-04, kingshammer.** A route-fixture seed could be satisfied by content the real build would drop as inert, adopted a same-slug route without comparing its target list id, adopted a route behind an inactive club, fanned out over the reserved `hq` record, and fell back to the generic CMA token.
  Lesson: judge found content by the build's rules, compare adopted payloads to the plan, pin the script to its one sandbox, refuse the generic token.
- **2026-07-20, kingshammer.** A form seed made live writes on release day that could strand a visitor (redirect to an unpublished destination) and rewrote footer navigation and disabled a legacy proxy as side effects.
  Lesson: create risky live records disabled, leave already-enabled records alone on rerun, and move cutover actions out of seeds into a documented human step.
- **Ample-co Stack 52 (Codex).** A recovered Page-to-Post converter deleted converted pages when the stated behaviour was to unpublish them for recoverability.
  Lesson: decide and encode the destructive contract (unpublish vs delete) before running any conversion.

## Partial failures

- **2026-03-13, kingshammer.** `migrate-content-placement.ts --env=club-row-migration` completed all R1 mutations, then in the first R2 created a replacement carousel, updated the page, destroyed the old row, and crashed in the heading-reference check. The removed heading was left as an orphan; on rerun the preflight would see the old row gone and skip, never cleaning it up. Jake asked "do I need to go ahead and refork my sandboxes?" The answer was no for the earlier pre-write 422, yes once real writes had landed.
  Lesson: after any write, a crash means re-fork rather than rerun. "Only run on fresh forks" does not cover rerun-after-partial-failure.
- **2026-08-19, kingshammer Camps.** All six `camps` sandboxes were deleted; HQ was re-forked and ran three migrations; the fourth failed with `VALIDATION_PLURAL` (`additional_programs`). Five projects were not yet re-forked. The agent stopped, reported exact state, and refused to continue until the cause was proven.
  Lesson: that stop is the desired behaviour. Dry-run the schema against one project before deleting environments in all of them.
- **2026-08-20, kingshammer Camps.** A seed against a fresh Cincinnati fork stopped because the expected club page with slug `programs` did not exist. The agent inspected the inventory rather than synthesizing a replacement.
  Lesson: a missing placement target means the sandbox diverged from the assumption; investigate, never invent records or weaken the preflight.

## Wrong-environment wiring

- **2026-08-10, ample-co.** A build failed with `Field 'allPosts' doesn't exist`. The resolved Netlify config had the token but no environment entry, so the build silently queried primary.
- **2026-08-25, mikealbert.** A branch-scoped Netlify variable was set to `fsl-newsletter-drawer` before that sandbox existed; the preview failed.
- **2026-08-25, ample-co.** Jake pasted the Dato environment value into the Contentful variable; a preview failed "bc it was pointing at wrong dato env".
- **2026-08-20, kingshammer.** A local run silently loaded `.env.local` values not pointing at `camps`.
- **2026-08-26, mikealbert.** An FSL migration dry run showed it would also apply the unrelated `20260807120000_oemStartupPage.js`, because a fresh fork has an empty ledger. Only the intended file was symlinked into a temp `--migrations-dir`.
  Lesson for all: wiring is an ordered step (create sandbox, then set the variable by branch, name, and value, then rebuild); echo the resolved environment before every run; read the dry run's script list.

## Lost tooling and false premises

- **2026-08-10, ample-co.** The agent told Jake the migrations "did not exist as code" and hand-wrote a `createPostModel.js` with two real errors (`slug` type, `api_key` casing). The migrations existed the whole time in gitignored `.scratch/tools/`. The same absence had made losing the `cms-restructure` environment look like losing the ability to rebuild it. Jake reversed his throwaway-tooling stance: "I agree they should be committed."
  Lesson: search outside git before concluding tooling does not exist; commit the migrations and seeds that make an environment reproducible.
- **2026-08-10, ample-co.** The agent claimed `DynamicCollection.entries` was "deleted by the restructure" and proposed restoring it. It was a new field added to `main` after the fork.
  Lesson: environment differences are fork-timeline artifacts; diff and check when a field was added before naming a cause.
- **2026-07-30, ample-co.** A 29-ticket spec rested on introspection evidence that described the old Contentful schema, not DatoCMS. The first implementer stopped without writing code; the spec was rewritten into 15 tickets.
  Lesson: verify the spec's claims read-only against the live CMS, two independent ways, before executing any ticket.
- **2026-08-04, kingshammer.** An external review demanded a destroy migration for schema retired via the UI on sandboxes. The migration had never run in any primary; the destructive work had been done by an untracked runner.
  Lesson: whether a destroy migration is warranted depends on whether the schema reached primary; check git history and merge base rather than accepting the premise, and prefer amending a never-run migration.

## Scope and evidence failures

- **The Ample DatoCMS incident (recounted 2026-08-04).** While creating a new `Post` content type, an agent built an entire unrequested backward-compatibility layer. "Never asked it to do that and it was confusing and then I had to waste time figuring out what it was even doing." Origin of the no-backward-compatibility rule in Jake's baseline docs.
- **2026-08-25, ample-co PR #65.** The diff reached ~26k lines because migration tooling, capture scripts, evidence artifacts, and process docs were committed alongside the migrations. Jake: "give me a list of what is in there and I will tell you exactly what needs to go."
- **2026-08-25, mikealbert FSL.** Code-complete was nearly reported as done. Jake: "I forgot. we didn't actually do the work in dato yet did. the sandbox work."
  Lesson: CMS setup is a distinct release gate; enumerate the missing CMS, build, browser, and integration checkpoints.
- **2026-08-24, ample-co.** A reconciliation audit found 11 posts with lost words, 6 with conversion debris, 10 missing captions, 114 differing dates from the earlier Webflow-to-Dato migration, none surfaced by a green build. Jake: "evidence is key here", before, after, and production control screenshots on the PR.
- **2026-08-22, mikealbert.** A prototype cleanup deleted an untracked `.playwright-mcp` directory.
  Lesson: never delete untracked working-tree artifacts during cleanup without permission.
- **2026-07-30, ample-co overnight run.** Two decisions were made while Jake slept: a new ticket for an unowned surface, and deletion of a 325-line dead template outside the ticket's file list. Both were disclosed with exact reverts in the morning report.
  Lesson: autonomous decisions in unattended runs are acceptable only when reversible, disclosed first, and accompanied by the undo. Widening a ticket silently is not.
