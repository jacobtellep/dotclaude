# Contentful guard patterns

The patterns below come from `worldpay-com/scripts/contentful/contact-flow/safety.js`, the product-finder helpers in the `fc25` worktree, and the Clark Schaefer `contentful-migration` script. Reuse the shape and the refusal text. Pin every guard with a unit test on fakes that fails if the guard is deleted; the worldpay suite proves alias refusal at all five entry points with zero mutation events and never touches a live space.

## Contents

- Hardcoded target with redundant confirmation
- Alias refusal
- Live target confirmation
- Plan by default, blockers abort everything
- Reviewed-plan binding for production
- Read-only tools that cannot mutate
- Destructive confirmation and completeness proofs
- Content-type three outcomes and fail-closed migrations
- Shared-entry and state refusals
- Locale guards
- Rate limiting and pacing
- Token hygiene and legible refusals
- Sanctioned override

## Hardcoded target with redundant confirmation

```js
const APPROVED_SPACE_ID = "<space>";
const APPROVED_ENVIRONMENT_ID = "<sandbox>";
// Refusing to run: environment must be exactly "<sandbox>".
// Refusing to run: space must be exactly "<space>".
```

Applies to plans, not only applies. On `--apply`, additionally require `--space` and `--environment` explicitly and require `NEXT_PUBLIC_CONTENTFUL_SPACE_ID` and `NEXT_PUBLIC_CONTENTFUL_ENV` to equal them exactly:

```
Refusing to apply: pass --environment <id> explicitly.
Refusing to apply: environment variable must be exactly "<id>".
```

`resolveTargetEnvironment()` in the helpers also refuses when `CONTENTFUL_ENV` and `NEXT_PUBLIC_CONTENTFUL_ENV` are both set and disagree, refuses when neither is set, and refuses `master` unless a named `--allow-master-...` flag is present. Observed: `Refusing to run: CONTENTFUL_ENV/NEXT_PUBLIC_CONTENTFUL_ENV must resolve to contact-flow. Got master.`

When the sandbox is renamed, rename the guard constant, the script filenames, and the npm script names together, so no command name points at a stale environment.

## Alias refusal

Copy `sys.aliasedEnvironment` onto the inventory read and refuse:

```
Refusing to run: environment "<id>" is an alias for "<aliased>"; target the concrete <sandbox> environment.
```

Enforce at every inventory-facing entry point and re-check against the live connection's own `sys` in every apply (`assertLiveEnvironmentTarget`), so a clean plan against a live alias still refuses before any write. Fail closed when the alias link id is missing (`"unknown"`). Production `master` is the one target deliberately allowed to be an alias.

## Live target confirmation

`assertTargetEnvironment()` GETs the environment and throws `Refusing to run: CMA target resolved to <actual>, expected <intended>.` Ticket briefs phrase it as "verify that the environment id is exactly `<sandbox>` immediately before apply".

## Plan by default, blockers abort everything

```js
if (config.mode === "plan") { log("No Contentful writes were performed."); return plan; }
if (phase === "verify" && config.mode === "apply") throw new Error("Verification is read-only; remove --apply.");
throw new Error("Contentful apply is blocked: " + plan.blockers.join(" "));
```

Blockers name numbers: `Contact Flow needs 2 available content-type slots; found 0.` A blocker aborts the whole apply; the docs must say so, or an operator reads "entry X was skipped" as "the other 30 went out". Plans are pure functions over a normalized inventory read, which is what makes them unit-testable and trustworthy as previews. Unknown flags throw `Unexpected argument: <x>`; a flag without a value throws `Missing value for <x>`.

## Reviewed-plan binding for production

The production plan prints a deterministic `sha256:` digest over canonical JSON of the plan. Apply requires `--reviewed-plan "sha256:..."`, recomputes the plan from a fresh inventory, and refuses on mismatch:

```
A reviewed production plan binding is required before apply.
The reviewed plan binding does not match the first production plan read.
Contentful production state changed after the reviewed plan.
```

The publication binding covers the complete current draft inventory, so any intervening draft edit invalidates it. Production commands live in their own namespace (`contentful:contact-flow:production:*`) so nobody reaches them by muscle memory.

## Read-only tools that cannot mutate

For anything that looks at master:

- Hardcode `REQUIRED_ENVIRONMENT_ID = "master"` and require `--confirm-master-readonly`.
- Use the CDA (`cdn.contentful.com`) with the delivery token, GET only, and print a banner saying so.
- `MUTATION_FLAGS = new Set(["--apply","--delete","--destroy","--publish","--unpublish","--write"])` and refuse the run if any is present: `Refusing to <action> with mutation flag <flag>.`

## Destructive confirmation and completeness proofs

- Deletion requires the environment guard plus a long, uniquely named flag: `--confirm-delete-legacy-product-finder-models-consolidate-product-finder`. `Refusing to delete legacy models without <flag>.`
- Before deleting, prove replacement content is complete: `consolidated entry <id> field <f> has N items in locale <l>, but the seed defines M. Every locale must match the seed before cleanup.`
- `Refusing to delete content type <id>: <n> entries still exist.` and `Refusing to delete <id>: archived entries require manual review first`.
- Delete entries before content types; Contentful refuses to delete a type with entries, archived included.
- Seed fixtures carry an `allowedEnvironments` list the script enforces: `Refusing to use seed <path>: target environment <id> is not in allowedEnvironments`.

## Content-type three outcomes and fail-closed migrations

Planner: missing, create; exact match, no-op; anything else, block for human review (`<id> exists but does not match the pinned production model.`). No update path.

`contentful-migration` scripts (`async function(migration, { makeRequest })`) GET the content type first and throw if absent, resolve the default locale from `/locales?limit=1000` and throw if none, and if the field already exists assert an exact match on both the field definition and the editor control and return without writing:

```
blockAccordion must exist before the FAQ mode migration can run
blockAccordion.isFaq exists with an incompatible field definition
blockAccordion.isFaq exists with an incompatible editor control
```

Never bulk-write default values onto existing entries to normalize them; use strict opt-in semantics in the application (`isFaq === true`).

## Shared-entry and state refusals

- `Dictionary entry <id> has draft changes outside contactFlow: filters, navigation, sections. Have an editor publish or discard those drafts before the Contact Flow publish.` Present on both sandbox and production targets.
- `<id> is archived; refusing to modify it.` / `... refusing to publish it.`
- `<id> has a published version; refusing to overwrite administrator-controlled content.`
- `<id> is production reference content and must never be published.` backed by three gates: the publish phase cannot name it, the plan blocks if it was published by hand, the readback fails if it finds it published. Its required field is left empty so Contentful itself refuses, and its internal title says `[Reference - do not publish]`.
- App installation writes merge additively and report the count: `Set 5 Contact Flow field-visibility rules, preserving 1 unrelated rules.`
- Help text is drift-repaired: a reworded or removed help text is named in the plan and rewritten on apply.

## Locale guards

- `The target environment has no default locale.` / `Refusing to run: could not determine default locale for <env>.`
- `mergeLocalizedFieldOverrides` merges into the existing locale map rather than replacing it.
- `flexPage <id> field <f> must be a localized object.`
- Removal refuses until every locale's counts match the seed.
- Audits print counts per locale, never a union.

## Rate limiting and pacing

`MIN_REQUEST_INTERVAL_MS = 300`, `MAX_REQUEST_ATTEMPTS = 6`, `BASE_BACKOFF_MS = 750`, `MAX_BACKOFF_MS = 10_000`, retry on 429/500/502/503/504, honour `X-Contentful-RateLimit-Reset`, add jitter. Jake asked for backoff "so we dont run into 429s" as a matter of course.

## Token hygiene and legible refusals

- `set -a; source .envrc; set +a`, or `loadEnvrc()` that parses `export KEY=VALUE` lines without executing the file and never overwrites an already-set process variable.
- `redactSecrets()` rewrites `Bearer ...` and `CFPAT-...`; `safePathname()` strips `access_token=`; `formatCliError()` reduces a CMA failure to status, message, resource, requestId. CMA errors arrive as a JSON string inside `error.message` and contain request details.
- `refuse(message)` is `console.error(message); process.exit(1)`. An early version leaked a stack trace from top-level setup, and an operator cannot tell a crash from a working guard.

## Sanctioned override

`CONTACT_FLOW_PRODUCTION_ENVIRONMENT_ID=<fork-id>` retargets every `production:*` command at a pre-cutover fork of master under the same guards: `master` itself is refused while set, the fork id must appear in `--environment` and the variable exactly, and each command prints `Production target overridden: CONTACT_FLOW_PRODUCTION_ENVIRONMENT_ID=<id>`. Unset it after the alias flip and re-plan against `master` expecting zero operations. It replaced a proposed hand-edit of the safety constant; a guard's escape hatch is reviewed and tested, never a hand edit.
