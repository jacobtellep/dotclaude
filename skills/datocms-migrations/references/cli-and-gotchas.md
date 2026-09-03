# @datocms/cli, CMA client, and wiring gotchas

## Contents

- CLI flag semantics
- Environment facts
- Migration authoring
- CMA client traps
- Deploy and local wiring
- Verification traps

## CLI flag semantics

- `migrations:run --source=<env> --destination=<new>` forks `source` into `destination` and migrates the new fork.
- `migrations:run --source=<env> --in-place` migrates `source` directly, no fork. Use this when Jake already forked the sandbox by hand.
- `migrations:run --in-place` with no `--source`, or a bare `migrations:run`, targets the token's default environment, which is primary. Both `ample-co` and `kingshammer-com` `npm run migrate` are bare. Always pass the environment.
- `--dry-run` previews. Read the list of scripts it names.
- `--migrations-dir=<dir>` narrows the run; symlink only the intended files into a temp dir when unrelated pending migrations appear.
- `environments:fork <source> <new>`: plain fork keeps primary writable. `--fast` locks the source against editors during the fork; `--force` pushes through while collaborators are editing and the docs warn it can destroy their in-progress work. Use neither.
- `environments:primary` prints the name on the last non-empty stdout line; wrappers use `--log-level=NONE` and take the last line.
- `environments:list --json` output shape is inconsistent enough that `migrate-all.ts` walks the tree for id and name values.
- `environments:promote` and `environments:destroy` exist. Agents do not run promote. Destroy needs its own dry run, exact-target validation, and authorization immediately before the call.
- Two major versions are in play: `@datocms/cli ^3` in kingshammer and ample-co, `@datocms/cli@^2` pinned in mikealbert docs. Migrations import `@datocms/cli/lib/cma-client-node`; standalone scripts import `@datocms/cma-client-node`.
- `npx --package=@datocms/cma-client-node node <script>` does not expose the package to the script; set `NODE_PATH` to the npx cache instead of installing into the project.

## Environment facts

- Blank or unset `DATOCMS_ENVIRONMENT` means primary. `client.ts` only sends `X-Environment` when the variable is set. An unset variable silently queries production.
- Names are cosmetic and renameable. Primary can be called anything. Ask for `meta.primary`.
- Promote replaces primary wholesale with the fork. Anything written to primary between the fork and the promote is discarded. Re-fork immediately before promoting; "nobody is editing primary" is a listed precondition.
- The demoted old primary is an instant rollback (promote it back) but only promptly, since rollback discards anything written after the promote. It is not a backup. Fork primary to a dated backup before promoting and keep it until the effort ships.
- A fresh fork gains everything primary has and loses everything the old sandbox added: models, records, plugin configuration. Web Previews plugin config had to be reinstalled by hand after a promote because the new primary was forked from an environment that never had it.
- A fresh fork has an empty `schema_migration` ledger, so `migrations:run` applies every pending file. A `schema_migration` model with zero records means the CLI touched the project once, not that migrations ran.
- Promoting a fork carries the `schema_migration` model into primary and exposes `allSchemaMigrations` in the delivery schema. Deleting it afterwards makes every migration look pending again to future forks.
- A migration that adds a field already present in a fresh fork fails on the duplicate. When re-forking from a newer primary, drop the migrations whose changes the fork already carries.
- Environment differences are fork-timeline artifacts, not deletions. A field missing from a sandbox is usually a field added to primary after the fork. Diff before describing a gap.
- A promote does not trigger a build unless a webhook exists (ample-co had none). Webhook rebuild filters are per model and go stale; a model missing from the filter never triggers a build.

## Migration authoring

- `api_key` is snake_case (`published_at`, `hero_image`) even though GraphQL fields come back camelCase.
- Model API keys must be singular. `additional_programs` failed with `VALIDATION_PLURAL` and aborted a six-project rebuild after the environments were already deleted. Dry-run the schema against one project first.
- `publishedAt` maps to `date_time`, not `date`.
- Do not use the `slug` field type for legacy slugs; its validator can reject a real slug containing `---`. Use `string` with a `unique` validator.
- `buildBlockRecord` returns the JSON:API shape, not the simple record shape; mixing them produces malformed structured text silently.
- Annotate field arrays as `SimpleSchemaTypes.FieldCreateSchema[]`; an unannotated array widens `field_type` to `string` and fails to compile.
- Field position is not stable across environments. Pin every field's `position` in a canonical order or reconciled and fresh environments end up with different editor layouts.
- New models must be added to `SIDEBAR_CONFIG` in kingshammer's `migrations/1773102400_organizeSidebar.ts` and that migration re-run, or editors never see the model. Sidebar entries added before the model exists silently never take effect.
- Enabling `draft_mode_active` on an existing model changes editor behaviour: edits save as drafts and only publishing deploys them. Draft mode plus a published-only build token means unpublished records vanish from the site with no error.
- GraphQL introspection cannot reveal editor configuration. `String` is ambiguous between `string`, `text`, and `slug`; validators, widgets, and appearance params are invisible. A migration reconstructed from introspection is a guess; prefer a real migration file, and search outside git (gitignored scratch dirs, sibling worktrees, old sessions) before concluding none exists.
- Link field `on_reference_delete_strategy` defaults to `delete_references`, which blanks the link silently. Use `'fail'` where a silent detach reroutes behaviour.

## CMA client traps

- `items.list` defaults to 20 records, max 500. Nested reads cap at 30 per page. Use `listPagedIterator` or collect all pages; realistic counts have landed within a couple of records of the default and silently truncated safety checks.
- Read at `version: 'current'` when checking existence; an unpublished record must still count or the run creates a duplicate on its slug.
- Records expose fields directly or under `record.attributes` depending on the call. Normalize both shapes.
- Real field values carry human typos and whitespace (`-fields. publishedAt`). Trim parsed configuration values. Free-text options are a silent never-match hazard.
- The CMA rate-limits. Batch and pace large conversions; print the partial report before the error that stopped the run.
- "Create or adopt by slug" idempotence can certify a wrong state. Compare the adopted record's payload against the plan and report a mismatch rather than rewriting it.
- Shared records (rows, headings, blocks referenced by several pages) are the main correctness hazard in content migrations. Reject conflicting derived values instead of picking the first, and never destroy a record still referenced elsewhere.

## Deploy and local wiring

- Create the sandbox before pointing any branch variable at it. A preview failed because the branch variable named a sandbox that did not exist yet.
- Report branch name, exact variable name, and value together. Jake once pasted a Dato value into the Contentful variable when given only the value.
- `.env.local` is loaded silently and has redirected runs to the wrong sandbox. Echo the resolved environment and token source before any run.
- Netlify: `--context a,b,c` is parsed as a branch name; repeat `--context` per context. Branch-level overrides beat context values. A build log's resolved config reflects that build, not later edits; verify with `netlify env:get` per context.
- Forcing global Deploy Previews to a sandbox misleads every other open PR; scope the preview to the branch instead.
- Deleting a sandbox a local `.env.local` still points at breaks local builds with a 404. Blank (primary) tracks promotions automatically.
- Production request paths must send no environment header and honour no `DATOCMS_ENVIRONMENT*` override; a submission handler once read sandbox routing before writing real PII to a third party.
- The Web Previews plugin's endpoint field is prefilled with `https://`; pasting a full URL yields a malformed endpoint. Select all and retype.

## Verification traps

- Against the wrong environment, Astro reports `Field 'allPosts' doesn't exist on type 'Query'`, not an environment error. A Next build compiles and then fails page-data collection with `INVALID_AUTHORIZATION_HEADER` on a bad token; compilation is not build proof. Without network, `getaddrinfo ENOTFOUND graphql.datocms.com`.
- A green sandbox preview is not merge readiness; production may still point at an environment without the new model.
- A stacked PR can be un-buildable by design when the schema change and code change live in different PRs and no environment satisfies both. Collapse the stack or add the one missing field; do not treat a variable tweak as the fix.
- Verification counts come from the live environment, not the script's own log, which has double-counted.
- Third-party side effects (Constant Contact lists, Resend emails) do not roll back with an environment. Keep them read-only in QA and off in non-production unless explicitly overridden.
