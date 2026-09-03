---
name: datocms-migrations
description: Safety protocol for any DatoCMS schema or content work. Use before the first DatoCMS command in a session and whenever a task involves a Dato migration, seed, conversion, reconciliation, fork or sandbox environment, primary environment, promote, environment destroy, @datocms/cli, the CMA client, or a DATOCMS_* variable. Encodes Jake's standing rules from ample-co, kingshammer-com, and mikealbert-com: writes go only to one named non-primary sandbox, every write command dry-runs first, each write is separately authorized, results are verified by reading the environment back, and promotion is human-only.
---

# DatoCMS migration safety

Applies to every DatoCMS write: migrations, seeds, conversions, reconciliations, forks, destroys, promotes, and the env wiring that points a build or preview at an environment.

Jake, verbatim: "please do not touch the primary env. ever. that is very important. have reliable guards against it." and "the flow is and has always been to fork -> apply -> promote."

Agents fork, migrate, seed, verify, then stop. Jake promotes.

## Before the first command

State the boundary in one message and get it confirmed before any CMS call:

1. Project(s), and which environment is primary, read from `environments.list()` and `meta.primary`. Never infer primary from a name: `main`, `main-2026-08-12`, `main-post-migrations`, `production-2026-06-24` have all been primary, and a sandbox literally named `production` was not.
2. The one sandbox this work writes to, by exact name, and who forks it. Default: Jake, in the Dato UI, fresh from the current primary.
3. The write credential by variable name only, and confirmation it is a CMA token. The build's delivery token cannot write and fails with an opaque 401. A missing write token is a gate for Jake, never a reason to fall back to another token.
4. The git branch, its base, and the deploy-preview variable that pairs with the sandbox.
5. What stays Jake's: fork lifecycle, promote, Netlify env vars, merge and push, client contact.

Done when Jake confirms. His gate is literally "any safety things unclear? are we ready?".
If the spec's premise disagrees with the live schema (verify read-only with both `itemTypes.list()` and GraphQL introspection), stop and re-spec. Do not adapt the implementation to a wrong plan.

## Hard rules

- **Sandbox only.** Every write names its environment explicitly. Refuse a blank or omitted environment: blank means primary to the Dato client. Refuse primary by `meta.primary`. Refuse every other environment name too, sandbox or not. Reads from primary are fine when read-only and announced.
- **Dry run by default.** `--dry-run` is the default posture; `--apply` is opt-in; `--publish` needs `--apply`; a primary write needs `--allow-primary` plus its own separately approved cutover. Verify commands refuse `--apply`.
- **Authorization is explicit, narrow, and per step.** It names the environment ("run the seeds against the blog-test env only", "approve remaining sandbox migrations only and only in forms-test"). It arrives at the moment of the write, not bundled into an earlier plan approval. It does not carry over to the next ticket, environment, or phase. A question about what a tool can do is not authorization. When Jake is away, queue every human-only decision and write nothing past a gate.
- **Fork lifecycle and promote are Jake's.** Hand over exact commands or UI steps and stop. If a fork, destroy, or refork is delegated, it needs its own authorization immediately before the destructive call, after inventorying anything in the old sandbox not represented in code.
- **Schema lives in committed migrations.** Idempotent: look the model up by `api_key`, skip with a log line if present, resolve every referenced model before writing anything. A hand edit in the Dato UI is never source of truth. Unmerged work amends the migration in place; anything that has run in a primary gets a forward migration only.
- **Unpublish over delete.** Destroy a record only when two independent signals agree, after `listReferencesPagedIterator` shows nothing still points at it. On disagreement, refuse the whole run.
- **Seeds write only what the feature owns.** Drafts by default; when a model has draft mode on, publish converted records explicitly or the build silently drops them. Journal every created ID to a ledger before creating it; tear down by ledger ID only, never by name or query. Adopted records that disagree with the plan are reported, never rewritten.
- **No compatibility shims.** Migrate forward and delete the old path. Unrequested backward compatibility around a new content type is the incident Jake still cites.
- **Verify against the environment, not the log.** Read back: target still non-primary, ledger entries, record and published counts via the delivery API, zero duplicate slugs, primary unchanged. Re-run the dry run and require nothing pending. Build against the sandbox and open a rendered page. Say what was file-backed and what was only observed live.
- **Tokens never appear** in output, logs, commits, or generated artifacts.
- **Report the write scope** in every status: the sandbox by name, what was written, what was only read, what is not done. Code-only work is never "production ready".

## Workflow

Each step ends when its criterion is met. Later steps do not start early.

1. **Inventory, read-only.** `environments:list --json` with an unscoped client. Record the primary id, confirm the target exists, `status` is `ready`, and it is not read-only.
2. **Fresh fork.** Jake forks from the current primary (plain fork, no `--fast`, no `--force`). Prove zero drift with a read-only schema comparison before the first write, and report it with numbers ("20 models, 132 fields, 0 writes").
3. **Wire the environment.** Report branch name, exact variable name, and value; Jake sets it. The sandbox must exist before any variable points at it.
4. **Dry-run the migrations and read the list.** A fresh fork has an empty `schema_migration` ledger, so every pending file in the directory will run, including unrelated features. Narrow `--migrations-dir` to a temp dir holding only the intended files if anything unexpected appears.
5. **Apply to the sandbox** with `--source=<sandbox> --in-place`, after authorization. Re-run the dry run: "No new migration scripts to run" is the criterion.
6. **Regenerate types** (`npm run types:generate` where it exists) and typecheck. The compiler is the first schema test.
7. **Seed.** Dry run, compare counts to the number the spec predicts, authorize, apply, run again and require a no-op. Batch and pace large runs; print the partial report before any failure so a crashed run leaves a record.
8. **Read back and build.** The readback list above, then a full build with the sandbox variable set and a browser check of the affected routes. Screenshots plus "how to test it yourself" are the evidence Jake asks for.
9. **Package the PR.** Commit the final migrations and product code. One-off tooling, test-content seeds, and agent artifacts stay out unless Jake says otherwise. Label seeded content as test data. The `pr-description` skill governs the body. Commit and push only on his word.
10. **Promote package for Jake.** Preconditions (nobody editing primary, sandbox re-forked from current primary), back up primary by forking it first, the UI promote steps, the post-promote audit (every hardcoded environment name in Netlify contexts, `.env.local`, preview plugin config; blank is primary and tracks future promotes), the rollback (re-promote the demoted environment, promptly or never), and an explicit list of what the package does not do.
11. **Clean up only what you created**, and only when the effort has shipped. Flag stray environments and processes; do not remove them.

## Partial failure

Never rerun blindly. Enumerate exactly what was mutated. A failure before the first write is safe to retry; a crash after any write means the sandbox is contaminated and should be re-forked, because an idempotent rerun will skip the half-done step and leave orphans behind.

## Multi-project estates (kingshammer HQ plus hubs)

Bind each write token to its tracked project id before writing; a token plus a matching environment name can belong to a different project. Refuse the generic token fallback. Scope fan-out with `DATOCMS_SITE_SCOPE` and validate the resolved target list. Preflight every project before the first write, write hubs before HQ, and require the complete tracked inventory for any destructive fan-out. Dry-run the schema against one project before deleting environments in all of them.

## References

- [references/guards.md](references/guards.md): the guard patterns that have held up, with the code shapes and refusal text to reuse.
- [references/cli-and-gotchas.md](references/cli-and-gotchas.md): `@datocms/cli` flag semantics, CMA client traps, environment and deploy wiring pitfalls.
- [references/incidents.md](references/incidents.md): what went wrong before, dated, with the lesson each one left.
- [references/repos.md](references/repos.md): per-repo variable names, scripts, sandbox naming, and the docs to read first.
