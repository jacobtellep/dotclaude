# Per-repo notes (Contentful)

What the repo's own files do not confess. Read the repo's `CLAUDE.md`, `AGENTS.md`, `CONTEXT.md`, untracked `CODING_STANDARDS.md` (by direct path), and `docs/*.md` first; closer guidance wins.

## Contents

- worldpay-com
- clarkschaeferconsulting-com
- SibcyClineWebsite
- necco-org
- crossroads (legacy Ruby framework)
- Environment naming seen so far

## worldpay-com

- Next.js, single space (`zhwqbd2ar3b8`), 22 locales with default `en`. Production `master` is an alias and sat at the 75 content-type cap.
- Variables: `CONTENTFUL_MANAGEMENT_TOKEN` (CMA, required even for plans), `NEXT_PUBLIC_CONTENTFUL_SPACE_ID`, `NEXT_PUBLIC_CONTENTFUL_ENV` (site-wide), `NEXT_PUBLIC_CONTENTFUL_DELIVERY_TOKEN`, `CONTENTFUL_PREVIEW_TOKEN`, `CONTACT_FLOW_PRODUCTION_ENVIRONMENT_ID` (sanctioned pre-cutover override), `CONTACT_FLOW_REVIEWED_PLAN`, `CONTACT_FLOW_MARKETO_DRY_RUN`, `CONTACT_FLOW_MARKETO_SUBMIT_ALLOWED_FORM_IDS`, `SITE_URL` / `DEPLOY_PRIME_URL`.
- Committed CMA tooling in `scripts/contentful/contact-flow/`: `phase-index.js <isolated|production> <migration|seed|publish|verify>`, `safety.js`, `isolated.js`, `production.js`, `contentful.js`, `definitions.js`, and the 291-line `README.md` runbook. Zero occurrences of `delete` in the plan builders. Test suite `src/__tests__/contact-flow-contentful-tooling.test.ts` runs entirely on fakes.
- npm scripts: `contentful:contact-flow:{migrate,seed,publish,verify}` and `contentful:contact-flow:production:{migrate,seed,publish,verify}`. No combined apply. `generate:contact-flow` builds the committed-at-build snapshot; it emits an empty snapshot for zero published flows but returns 400 if the content type is absent, so the production migration is a prerequisite of the code merge.
- Environments: `contact-flow` (sandbox, called `isolated` in code, cloned from `wp-dev-test`), `wp-dev-test` (clone source), `master-<YYYYMMDD>` pre-cutover forks, `uat`, `content-test`, `master-*` snapshots (off limits).
- Local issue tracker: `.scratch/<feature-slug>/{spec.md,issues/NN-*.md,evidence/}` per `docs/agents/issue-tracker.md`. Authorization gates and write-scope statements live there. Evidence kept out of git via `.git/info/exclude`.
- ADRs in `docs/contact-flow/000{1,2,3,4}-*.md` explain the surprising bits: production reference content that must never publish (0003), preview resolving draft schemas at request time (0004).
- Cutover so far: migrate phase only was run against `master-20260804` on 2026-08-04, then Jake flipped the alias. Seed and publish to production remain unrun and separately gated. The product-finder consolidation tooling (2026-05, PR #378) lives in `~/.codex/worktrees/fc25/worldpay-com/scripts/contentful/` as local artifacts, deliberately out of the PR.
- Git state has surprised before: check `git branch --show-current`, `git status --short --branch`, PR head, and remote refs before routing.

## clarkschaeferconsulting-com

- Monorepo, two sites, two spaces: Consulting `45fgz00aw4jj` (`packages/csc-com`), Hackett `fldcb3509v6k` (`packages/csh-com`). A parity change means two migrations, two sandboxes, two verifications.
- Variables: `NEXT_PUBLIC_CONTENTFUL_SPACE_ID`, `NEXT_PUBLIC_CONTENTFUL_ENV` (defaults to `master` when unset), `NEXT_PUBLIC_CONTENTFUL_ACCESS_TOKEN` (delivery), `NEXT_PUBLIC_CONTENTFUL_PREVIEW_ACCESS_TOKEN`. Set in both `.env` and `.envrc`; direnv wins.
- `PROJECT.md` states the house posture: "No Migrations: Content model changes managed directly in Contentful UI." Schema snapshots are committed (`packages/*/contentful-schema.json`, `schema/content-types.json` imported with `contentful space import`, which reads the environment from the variable with no guard of its own).
- The one migration script, `scripts/contentful/migrations/20260820-add-faq-mode.js`, is an untracked local artifact: fail-closed `contentful-migration` module run with `contentful space migration --space-id <id> --environment-id faq-accordion`.
- The safe-cloning research doc with the 15-step checklist was removed from the branch in `6d556415`; recover with `git show 6d556415^:docs/research/2026-08-20-contentful-sandbox-cloning.md`.
- Sandbox `faq-accordion`, cloned from `master`, in each space. Local QA on `localhost:3000` / `3001` with per-process env override.

## SibcyClineWebsite

- Gatsby/Next hybrid reading Contentful `master` via GraphQL in `src/lib/cms/gql.js`; `getServerSideProps` on community pages means CMS publishes hit production instantly. `NEXT_PUBLIC_CONTENTFUL_ENV` defaults to `master`.
- PR #1406 (`fix/tolerate-unresolvable-links`) centralizes `UNRESOLVABLE_LINK` tolerance in `GQL.fetch`, replacing five string-match copies.
- Working pattern Jake set: branch off `staging`, implement, validate, leave uncommitted for his review; answer stakeholder questions before implementing the fix.

## necco-org

- Contentful `master` reviewed read-only during the 2026-08-12 SEO audit; no content writes. Remediation tracked as Asana tasks for humans.

## crossroads (legacy Ruby framework)

- `crossroads/crds-contentful-migrations`: `bundle exec rake contentful_migrations:{new,pending,migrate,rollback}`, `rake seed_data`. Variables `CONTENTFUL_MANAGEMENT_ACCESS_TOKEN`, `CONTENTFUL_SPACE_ID`, `CONTENTFUL_ENV` (defaults to `master`; always set it), `MIGRATION_PATH`.
- Worth borrowing: `pending` to preview, `RevertibleMigration` for automatic `down`, seed data as markdown so QA can repopulate environments created from `master`.

## Environment naming seen so far

- `master` (production, alias), `master-<YYYYMMDD>` (pre-cutover fork), feature-named sandboxes (`contact-flow`, `consolidate-product-finder`, `faq-accordion`), named clone source (`wp-dev-test`), `uat`, `content-test`.
- Sandboxes are named for the feature, cloned from master or the launch-shaped source, and disposable. When the name changes, change the guard constant, filenames, and npm script names together.
