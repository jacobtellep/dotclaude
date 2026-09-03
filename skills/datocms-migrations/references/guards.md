# DatoCMS guard patterns

The patterns below survived adversarial review and real runs. Reuse the shape and the refusal text. A guard with no test is a comment: pin each one with a unit test that fails if the guard is deleted, using an injected fake client, and test it at the real entry point (tests that inject their own config once passed straight through a guard).

## Contents

- Layered target guard
- Exact-name allowlist
- Structural write confinement
- Flag escalation
- Creation ledger and ledgered teardown
- Project-id binding (multi-project)
- Dry run that reaches zero credentials
- Destructive preflights
- Readback verification
- Token hygiene
- Fail closed
- Known residual holes

## Layered target guard

Order matters. A refusal must abort locally; it must never mean a write reached primary and the server declined it.

1. **Parse time, no network, no credential.** Refuse a blank target outright.
   ```
   No target environment given. Name the sandbox explicitly. An omitted environment means the primary environment, which this harness never writes to.
   ```
2. **Live check with an unscoped client.** `environments.list()`, find `meta.primary`, then:
   - refuse if the target is primary: `Refusing to convert in "<env>": it is this project's primary environment. Run this in a sandbox forked from primary.`
   - refuse if primary cannot be determined: `Could not determine which environment is primary, so no write can be proven safe.`
   - refuse if the target does not exist: `Environment "<env>" does not exist. Fork it from primary in the DatoCMS UI first.`
   - refuse if `status !== "ready"` or `meta.read_only_mode`.
   Build the listing client unscoped; an environment-scoped client rejects unknown names with a raw API error before your checks run.
3. **Re-check immediately before each write** on long-lived clients. A sandbox can be promoted at any moment, so a one-time check is a TOCTOU hole. The stronger fix is a dedicated token whose role has `environments_access: sandbox_only`, verified by token id, with no general-token fallback.

Reference implementations: `ample-co/scripts/seeds/seed-posts-from-pages.ts` (asks the project which env is primary, "so renaming one cannot smuggle a write past"), `kingshammer-com/scripts/seeds/seed-hub-routing-test-content.ts` (`assertSandboxEnvironment`), `worktrees/ample-co/cms-restructure/.scratch/tools/cms/guard.ts` (`assertSandbox` then `assertLiveSandbox`, distinct exit codes: 0 ok, 1 verification failed, 2 bad args, 3 refused).

## Exact-name allowlist

"Any non-primary environment" is not enough; it lets a script write into a colleague's or a client's sandbox. Pin the one authorized name:

```ts
const REQUIRED_ENVIRONMENT = 'forms-test'
// --env must be "forms-test"; hub routing test content is seeded into that sandbox only, not "<env>"
```

Keep the name out of shipping code where possible: read it from configuration (`DATOCMS_PREVIEW_ENVIRONMENT`) so re-forking is a config change, and still refuse a blank value.

## Structural write confinement

Enforcing the rule at the CLI seam is insufficient, because migration and seed scripts do not pass through that seam. Make it a type-level property:

- `readClient(environment?)` returns an interface exposing only `list` methods.
- `sandboxWriteClient()` takes no environment argument at all. "There is no spelling of the write factory that aims anywhere but the sandbox."
- Drift and verify modules accept a `SchemaReader` interface with no write method.
- The harness has no `env:fork`, `env:destroy`, or `env:promote` command and never calls those APIs.

## Flag escalation

Default invocation reports and writes nothing.

- `--dry-run` explicit and the default; `--dry-run` and `--apply` mutually exclusive (`Choose exactly one operation mode`).
- `--apply` to write drafts.
- `--publish` requires `--apply`.
- `--allow-primary` required on top for a primary write: "Primary is refused by default. Add `--allow-primary` only for the separately approved cutover."
- `--apply` requires `--ledger=<new-path>`; `--teardown-ledger` cannot combine with `--apply` or `--ledger`.
- Unknown flags are rejected, not ignored (`Unknown option: <arg>`). A script once silently ignored `--dry-run` because `main` never parsed `process.argv`.
- Promotion in the kingshammer release path needs `MIGRATE_EXECUTE=1`, `MIGRATE_ALLOW_PROMOTE=1`, `ALLOW_DATO_PROMOTE=1`, and a sandbox name matching `^(release|migrate)-[a-z0-9][a-z0-9-]*$`. Two independent switches plus a name pattern.

## Creation ledger and ledgered teardown

- Generate the record id client-side (`generateId()`), append it to a JSONL ledger, then create with that id. A lost API response cannot orphan a record.
- Ledger header records environment and project; every entry records `projectSlug`, `projectId`, `recordId`.
- Refuse to overwrite a non-empty ledger.
- Teardown validates every entry against the verified client, destroys only listed ids, tolerates 404, and never deletes by name or query.
- Distinguish created records from adopted records; adopted ones are never torn down.

Reference: `kingshammer-com/scripts/seeds/forms-test-creation-ledger.ts`.

## Project-id binding (multi-project)

An environment-name guard cannot see which project a token owns. Before any write or delete:

- Resolve the project id from the token (`site.find()` / `fetchProjectId`) and compare to the tracked inventory. Refuse on mismatch, duplicate assignment, or an unmapped target.
- Refuse the generic fallback token: `Hub project "<slug>" has no hub-specific token; refusing the generic DATOCMS_CMA_API_TOKEN`.
- For destructive fan-out, require exactly the tracked inventory (`missing:`, `extra:`, `duplicate:`, `missing token:`) and print `name [project id]` for every target during dry run.

References: `kingshammer-com/scripts/lib/routing-notification-project-binding.ts`, `worktrees/kingshammer-camps-follow-up/scripts/lib/environment-destruction.ts`.

## Dry run that reaches zero credentials

The best dry run resolves no credentials and calls nothing (the Camps seed). Where that is impossible, print the full per-project plan before any mutation and end with `Dry run complete. No DatoCMS mutating API was called. Re-run with --apply only after reviewing every project action above.` A dry run must not lazily create its own bookkeeping model.

## Destructive preflights

- Before dropping a field, scan `current` and `published` versions of every record for a configured value and refuse with the record id. Re-check immediately before `fields.destroy()`. Verify absence afterwards.
- Before destroying a record, `items.listReferencesPagedIterator` must be empty; never destroy a row, heading, or block still referenced by another page.
- Delete a page only when two independent signals agree (for example a routing heuristic and the converted post records); any disagreement refuses the run and deletes nothing.
- Prefer `on_reference_delete_strategy: 'fail'` on link fields where a silent detach would change behaviour invisibly (routing links). `delete_references` blanks the link silently.
- Preflight every target before the first write so a failure on project four leaves projects one to three untouched.

## Readback verification

After every apply, re-read the environment and assert the exact intended shape: validators, appearance, pinned field order, absence of deleted fields, ledger entries, record and published counts, zero duplicate slugs, target still non-primary, primary unchanged. Then re-run the dry run and require nothing pending. Schema comparison uses subset semantics on validators, not strict equality, or defaults re-PATCH every run.

## Token hygiene

- Redact `--api-token=` in every echoed command (`redactCommand`).
- Never print, log, commit, or generate an artifact containing a token; generated registries have carried per-project tokens.
- Store per-project CMA tokens in plugin global parameters (CMA-only), never in model fields (Delivery API exposes them).
- Keep the write token a separate variable from the build's delivery token, so a leaked build token cannot migrate anything.

## Fail closed

Malformed input is a refusal, not an absence. Reviews found preflights that turned malformed validators into `{}`, accepted stale record versions, and documentation claiming a sandbox guard the migration did not have. A guard that claims more than it enforces is worse than none.

## Known residual holes

- The live check lists environments, then writes proceed through a separately built client; a rename or promote landing between the two is not caught. That is why the name allowlist, not the live check, is the layer the invariant rests on.
- `ensureSandboxEnvironment` treats "already exists" during fork as benign, so a name collision with someone else's sandbox is adopted, not rejected.
