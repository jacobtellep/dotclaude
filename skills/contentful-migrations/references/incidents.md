# Contentful incidents and lessons

Dated, from Claude Code and Codex sessions. Each one is a rule in `SKILL.md`; this file is the reason behind it.

## Contents

- Production outage
- Shared-content writes
- Locale blind spots
- Guards that were missing or too rigid
- Environment and wiring surprises
- Evidence and scope failures

## Production outage

- **2026-08-11 to 08-13, SibcyClineWebsite.** An editor published the `Country Applefest` event whose `featuredImage` linked to an asset left unpublished in `master`. Contentful's GraphQL API returned 200 with complete data plus one `UNRESOLVABLE_LINK` error; the community page code threw on any `data.errors`. The event was linked to two metros, so 190 of 350 community pages returned 500, 69 of them with no events of their own. `getServerSideProps` meant it started the instant Publish was clicked, with no deploy and no stale copy to fall back on. Jake published the asset himself and asked for a durable safeguard: "my only concern is the content showing up incorrectly silently. warnings are not getting anyones attention."
  Lesson: one unpublished asset can take down hundreds of pages. Tolerate exactly `UNRESOLVABLE_LINK`, centrally, log it, keep everything else loud. The CMS UI cannot show this failure; only the Delivery API can. Contentful cannot be configured to prevent it.

## Shared-content writes

- **2026-05-20, worldpay-com product-finder consolidation (Codex, PR #378).** The seed carried `linkedEntryFieldOverrides` for 24 shared `atomProductBundle` entries, writing `description`, `secondaryDescription`, `image`, and re-publishing them. They were added to normalize the sandbox for comparison and then ran on a sandbox freshly forked from master, mutating all 24. Jake: "you updated a bunch of atoms. are we going to need to do that in master? I don't want to inadvertantly update content that shouldn't be updated in master once this ships." The agent's first answer, drift correction, was rejected: a fresh fork should have produced zero writes. Fix (`6e711f1a`): overrides removed; the seed writes only the consolidated entry and verifies 56 linked resources exist. Jake deleted and re-forked the sandbox and the whole sequence was re-run from clean.
  Lesson: a seed writes only what the feature owns; shared entries are checked for existence, never updated or published. A sandbox mutated by a suspect script is no longer evidence.
- **2026-07-27, worldpay-com review-environment rebuild.** The fresh clone of `contact-flow` from `wp-dev-test` inherited the shared Dictionary entry `3KNYvIPfYQRWt36O23fTXF` with unpublished draft changes in `filters`, `navigation`, `sections` from other work. The publish plan refused by name; an administrator published the entry, then the Contact Flow publish proceeded over 30 entries. A `dictionaryPublishBlockers` guard shared by both targets was added, and Jake approved the runbook change as a deliberate scope exception.
  Lesson: clones inherit drafts, and Contentful publishes an entry whole. Block publication of any shared entry with draft changes outside your fields, name the fields, expect the same blocker in production.

## Locale blind spots

- **2026-05-20, worldpay-com.** The first master-versus-sandbox audit summarized entries as a union across locales and looked complete while master had 16 linked products for `/en` and 27 for `/en-GB`. Only `/en` had been browser-compared. Jake asked for a confidence percentage, then directed a complete read-only enumeration of master through the delivery token. The audit was rewritten per locale and the removal script hardened to refuse until every locale matches.
- **Same session.** The seed exported from the sandbox carried stale prototype `en-GB` values while the real data lived under `en`; the first merge implementation replaced a field's whole locale map. Changed so locales are preserved.
- **PR #396, worldpay-com.** Non-English Marketo form ids existed in `contact-flow` but not `master`; English being blank by design made English-only views identical and led to an incorrect "empty in every language" claim that Jake corrected.
  Lesson for all: verify per locale, merge locale maps, and state locale-specific differences precisely.

## Guards that were missing or too rigid

- **2026-07-27, worldpay-com (ticket pr396-feedback/08).** The tooling had no alias handling; an alias named like the isolated environment would have satisfied the environment-id guard and let a sandbox seed write into master. Fixed with alias refusal at all five entry points plus a live re-check at apply.
- **2026-08-04, worldpay-com.** Twenty-one minutes before a client meeting, Jake needed to migrate a fresh fork `master-20260804`, and `safety.js` hardcoded only `contact-flow` and `master`, so no command could target the fork, not even a plan. The agent's first proposal was a throwaway hand-edit of the constant; it was replaced with the reviewed `CONTACT_FLOW_PRODUCTION_ENVIRONMENT_ID` override, refusing `master` while set, printing a banner, covered by three policy tests and a two-directional CLI smoke test (commit `d326c3c8`). The agent also said out loud that using `production:*` commands against a fork "technically crosses the old no-production-commands rule".
  Lesson: hardcoded guards need a reviewed, tested escape hatch for the pre-cutover fork; never a hand edit of a safety constant.
- **2026-05-13, worldpay-com.** The first defensive script refused correctly but crashed with a raw stack trace during setup. Cleaned up so refusals are explicit and quiet.
- **Rename, 2026-05-20.** When the sandbox moved from `contact-flow` to `consolidate-product-finder`, guard constants were updated but filenames still said `contact-flow`. Fixed: "That avoids a misleading command name pointing at the wrong environment."

## Environment and wiring surprises

- **Content-type defaults, 2026-07-27.** `marketoInstance` carried a content-type default, so Contentful stamped it onto 15 of 24 seeded Contact Flow items that should never have had one. Proved fixed only by rebuilding the environment and re-running the create path; the old entries were born under the old default.
- **Delivery 404 on the fork, 2026-08-04.** The migration against `master-20260804` succeeded (management tokens see every environment) but `yarn build` failed: the CDA key's environment list did not include the fork. Jake ticked it in Settings, API keys, Environments.
- **Repointing main rejected, 2026-07-30.** Jake asked whether to point Netlify `main` at `contact-flow` until cutover. The agent argued against it on four grounds (site-wide selector serving seeded test pages live, silences the canary, makes all Marketo creds build-required, and the review environment was itself the target of destructive tooling rehearsals). Jake: "good call outs." The migrate-only phase against master was adopted instead.
- **Local dev against master, 2026-08-25, clarkschaeferconsulting-com.** CSH 500'd because `.env` pointed at `master`, which lacked `isFaq`. The agent named both options (repoint the variable, or migrate `master`) and said "I didn't want to touch either without you", then ran with a per-process override. Jake edited the env files. `.envrc` still exported `master` and would have won under direnv; the agent flagged it. CSC rendered fine on `master` against the same missing field, which the agent could not fully explain.
  Lesson: never migrate production to make a dev server work; enumerate every place the environment is set; a rendering page is not proof the field exists.
- **Capacity, whole project life, worldpay-com.** Production `master` sat at the 75 content-type cap; the two new types need two slots. The tooling refuses with `Production Contentful needs 2 available content-type slots; found 0.` Ticket 01 assigns freeing capacity to Worldpay's administrator. The production package has never been run, not even its plan.
  Lesson: a capacity blocker is expected behaviour. Never delete types to make room; never let a blocked dependency get reclassified as done.
- **Three weeks after cutover, 2026-08-25.** The client dev hit `Unknown Content Type: contactFormFlow` (a host built from a branch without the feature) and `marketoFormId has no Contentful value for en` (a destination that does not support English by design), and blamed `SITE_URL`. Jake could not recall whether master had been seeded: "master wasnt seeded. the content models were just put there. I think some things were seeded."
  Lesson: after a CMS migration, the code reading the new types must be deployed everywhere the environment is readable, and per-phase, per-environment records of what was applied must be written down.

## Evidence and scope failures

- **2026-07-27, worldpay-com.** Several evidence lines cited UI screenshots that stopped scrolling before the fields they claimed to show, including the one visibility rule the spec calls a correctness concern. Caught by an independent spec reviewer. Everything was re-captured and the evidence section rewritten to say which claims are file-backed. The same round caught a blocker message quoted with its second sentence truncated, which would have implied only one entry was skipped when the whole apply aborts.
- **Ticket 17, worldpay-com.** A report called a local file git-ignored when it was merely untracked, and said no Contentful plan had run when mocked plans had run inside Jest. Both corrected.
  Lesson: "no live Contentful plan ran; mocked plans ran in Jest" is the defensible claim.
- **2026-08-25, clarkschaeferconsulting-com.** An agent posted more PR review comments than it announced. Jake: "there are like a million comments. did you comment more than what you said you were gonna post?"
- **2026-08-20, clarkschaeferconsulting-com.** An agent implemented an unrequested FAQ accordion facelift, validated by 73 tests and lint, and treated it as done. Jake: "blow away all those changes. I don't like it." The pushed branch was also described as delivered when previews had not been checked.
- **2026-08-25, clarkschaeferconsulting-com.** A `cd && git stash` chain misfired and popped an unrelated stash onto the working tree; the agent restored the files and disclosed it.
- **2026-08-12, necco-org.** During an SEO audit of `master`, no content edit, save, or publish occurred; findings became Asana work for humans. The record states the session made no writes.
  Lesson: looking at production content is fine; changing it as a side effect of an audit is not, and the write scope is recorded either way.
