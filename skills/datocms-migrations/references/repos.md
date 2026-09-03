# Per-repo notes (DatoCMS)

What the repo's own files do not confess. Read the repo's `CLAUDE.md`, `AGENTS.md`, untracked `CODING_STANDARDS.md` (by direct path), `migrations/README.md`, and `docs/*.md` first; closer guidance wins.

## Contents

- Variable names mean different things per repo
- ample-co
- kingshammer-com
- mikealbert-com
- Sandbox naming seen so far

## Variable names mean different things per repo

| Variable | ample-co, mikealbert-com | kingshammer-com |
| --- | --- | --- |
| `DATOCMS_API_TOKEN` | read-only delivery token for builds | HQ CMA token (fallback for `DATOCMS_API_TOKEN_HQ`) |
| `DATOCMS_CMA_TOKEN` | full-access write token for migrations and seeds | not used |
| `DATOCMS_WRITE_TOKEN` | mikealbert write token (`.envrc`) | not used |
| `DATOCMS_CMA_API_TOKEN` | not used | generic hub fallback; guarded scripts refuse it |
| `DATOCMS_CMA_API_TOKEN_<HUB_SLUG>` | not used | per-hub write token |
| `DATOCMS_ENVIRONMENT` | read/build environment; blank means primary | same, plus `DATOCMS_ENVIRONMENT_HQ` for the HQ project |
| `DATOCMS_PREVIEW_ENVIRONMENT` | ample-co draft previews; blank refused | not used |

Confirm which name means what before authorizing a write.

## ample-co

- Single project. Astro site. Migrations in `./migrations` via `@datocms/cli`, ledger model `schema_migration` (`datocms.config.json`).
- Scripts: `migrate` (bare, targets primary unless flags are added), `migrate:dry-run`, `migrate:new`, `seed:posts -- --env=<sandbox> [--dry-run]`, `test:cms`.
- `scripts/seeds/seed-posts-from-pages.ts` is the reference guard: requires `--env`, asks the project which environment is primary, refuses it, refuses a missing environment, unpublishes replaced pages rather than deleting.
- `src/lib/datocms/client.ts` only sends `X-Environment` when `DATOCMS_ENVIRONMENT` is set. `src/lib/datocms/preview.ts` refuses a blank `DATOCMS_PREVIEW_ENVIRONMENT`.
- History: `cms-restructure` sandbox and worktree (July 2026, gitignored `.scratch/tools/` harness and the 534-line `promote-1-procedure.md` runbook), `blog-test` fork (Aug 10), promote of `main-2026-08-12` (Aug 12, Jake, UI), `blog-content-reconciliation-2026-08-24` sandbox and PR #65, `main-2026-08-26` fork awaiting Jake's promote.
- Jake's stance here: schema as code via `@datocms/cli`, "following what migration system kings hammer has would suffice", no bespoke runners. Commit the final migrations and seeds; keep one-off tooling out of the PR.

## kingshammer-com

- Multi-project: HQ plus five hub projects (cincinnati, tennessee, columbus, panama-city, central-florida), tracked project ids pinned in code. Next.js. 135+ migrations.
- Scripts: `migrate` (bare), `migrate:all -- <env> [--dry-run] [--promote]`, `migrate:hubs -- <env>`, `migrate:new`, `env:fork -- <name> [--source=]`, `env:destroy -- <name> [--dry-run]`, `seed:hub-routing-test -- --env=forms-test [--apply --ledger=<new> | --teardown-ledger=<path>]`, `reconcile:routing-notification-schema -- --env=forms-test [--apply]`, `types:generate`, `audit:routing-notifications`, `release -- <x.y.z>`.
- Scripts wrap Dato commands in `ntl dev:exec --` so Netlify-managed variables are injected.
- `lib/release/migrate-all-safety.ts` is the pure safety core: `shouldUseDryRun`, `getPromotionBlockers`, `isAllowedSandboxName`, `isTrustedCiContext`.
- `npm run release` is the only path that promotes; it turns execution and promotion on. Never reach for `release` when you mean `migrate:all`.
- `DATOCMS_SITE_SCOPE` (`hq`, `hq,tennessee`, `all`) narrows fan-out; unknown slugs only warn.
- Per-hub CMA tokens live in the kh-vault plugin's global parameters on HQ (`hub_tokens`), then `DATOCMS_CMA_API_TOKEN_<SLUG>`, then the refused generic fallback.
- Migration conventions: `migrations/<unix-ts>_<camelCase>.ts`, `export default async function (client: Client)`, existence check then skip, `migrations/utils/ensureField.ts`, new models added to `SIDEBAR_CONFIG` in `1773102400_organizeSidebar.ts`.
- Docs to read: `docs/RELEASES.md` (fork-migrate-promote, guardrails), `migrations/README.md` (immutability after primary, the narrow amend exception), `docs/FORMS.md`, `docs/FORMS-RELEASE-PLAN.md`, `worktrees/kingshammer-camps-follow-up/docs/CAMPS.md`.
- Release flow in Jake's words: lock deploys in Netlify, merge the code, pull main, run the normal release command to run the migrations and create a new release primary.
- Standing sandboxes: `forms-test` (exact-name allowlisted in seeds), `camps` (never promoted; name cannot match the release pattern).
- `scripts/destroy-environment.ts` gained exact project-id validation that Jake kept deliberately uncommitted; `CAMPS.md` withholds the runnable destroy command until the guard is accepted.

## mikealbert-com

- Single project. Next.js. Primary was `production-2026-06-24`; a sandbox literally named `production` exists and is not primary.
- Dato migrations and seeds live under `datocms/` on the unmerged `feature/fsl-newsletter-drawer` branch: `datocms/migrations/20260823120000_fslNewsletterDrawerFields.js`, `datocms/seeds/fsl-newsletter-drawer.js --environment=<sandbox> [--apply]`. Seed defaults to dry run, prints `{environment, mode, action, formId, landingId, wrote}`, refuses primary unless explicitly overridden.
- Write token is `DATOCMS_WRITE_TOKEN` via `source .envrc`, passed as `DATOCMS_CMA_TOKEN` to the seed. Read token variables: `NEXT_DATOCMS_API_TOKEN` / `DATOCMS_API_KEY`.
- The `datocms/README.md` there records the drift rule: fork close to release; re-fork and re-run if editors changed primary after the fork.
- Sandbox `fsl-newsletter-drawer` was forked by Jake on 2026-08-26; migrations and seed applied by the agent, promote pending with Jake.

## Sandbox naming seen so far

- Feature-named, long-lived: `cms-restructure`, `blog-test`, `forms-test`, `camps`, `fsl-newsletter-drawer`, `club-row-migration`.
- Dated promote candidates: `main-<YYYY-MM-DD>` (ample-co), `release-<x-y-z>` (kingshammer release path).
- Dated feature sandboxes: `<feature>-<YYYY-MM-DD>` (`blog-content-reconciliation-2026-08-24`).
- Tooling must never hardcode the name; take it as an explicit parameter.
