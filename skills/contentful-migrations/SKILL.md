---
name: contentful-migrations
description: Safety protocol for any Contentful content-model or content work. Use before the first Contentful command in a session and whenever a task involves a Contentful migration, seed, publish, content type change, environment clone or fork, master or an environment alias, contentful-cli, contentful-migration, the Management API (CMA), or a CONTENTFUL_* variable. Encodes Jake's standing rules from worldpay-com, clarkschaeferconsulting-com, SibcyClineWebsite, and necco-org: scripts refuse to run unless the target is exactly the named sandbox, every command plans by default, migrate, seed, publish, and verify are separately authorized phases, production is read through the Delivery API only, and the alias flip and environment lifecycle are human-only.
---

# Contentful migration safety

Applies to every Contentful write: content-type changes, entry seeds, publication, app-installation rules, environment clones, and the env wiring that points a build at an environment.

Jake, verbatim: "any script you write, needs to be very defensive and only runnable against the contact-flow env." and "when querying master, you must use the delivery token. you must be sure to make only read only queries against master."

Agents plan, apply to the sandbox, read back, and stop. Jake creates environments, flips the alias, and publishes.

## Before the first command

State the boundary in one message and get it confirmed before any CMS call:

1. Space id(s) and the concrete environment id of the sandbox. Sibling sites can be separate spaces (Clark Schaefer is two). `master` is normally an alias; resolve it to its concrete environment and record that id if it is the clone source.
2. Who creates the sandbox (default: Jake, in the Contentful UI or CLI, cloned from the environment closest to production at launch) and its exact name. Nothing an agent runs creates, deletes, renames, or re-aliases an environment.
3. The credential by variable name only: which is the management token, which is the delivery token. Production is read with the delivery token and the CDA, never the CMA.
4. Which variables select the environment for the build (`NEXT_PUBLIC_CONTENTFUL_ENV` and friends), where each is set (`.env`, `.envrc`, Netlify), and which one the running process actually resolves. These are site-wide selectors, never feature-wide.
5. What stays Jake's: environment lifecycle, alias flip, publication, content-type capacity, client contact, merge and push.

Done when Jake confirms. Re-state the constraint on every later authorization; he does.

## Hard rules

- **Sandbox only, by exact id.** Tooling hardcodes the approved space and environment and refuses everything else, `master` by name included, even for read-only plans. Apply requires the target in both the CLI flags and the environment variables, matching exactly. Refuse an alias as a write target by reading `sys.aliasedEnvironment`, at plan time and again against the live connection at apply time.
- **Plan by default.** Every command is a read-only plan until `--apply`. There is no combined apply. Plans end with `No Contentful writes were performed.` Verify refuses `--apply`. Any blocker (capacity, model divergence, target mismatch, archived entry, drift) aborts the entire apply with concrete numbers, not the offending item alone.
- **Four phases, four authorizations.** Migrate (schema), seed (drafts only, never publishes), publish (separately authorized, creates and updates nothing), verify (read-only). Authorization for one phase, ticket, or environment does not extend to the next. A capability question is not authorization. When Jake is away, queue decisions and write nothing past a gate.
- **Production is off limits until the cutover.** A production plan reads production, so do not run `production:*` commands at all, dry runs included, without separate authorization. Looking at master means CDA GET requests with the delivery token and a stated read-only banner.
- **Content types: create, no-op, or block.** Create when missing, no-op when it matches exactly, block for human review in any other shape. No update path; the tooling never rewrites a content type it did not create. Idempotent migrations fail closed on divergence and prove convergence by re-planning zero operations.
- **Seeds write only what the feature owns.** Linked and shared entries are checked for existence, never updated or published. Merge localized values into the existing locale map; a partial map deletes the other locales. Re-assert only structural fields; administrator-owned fields (labels, curated links, an explicit empty blocklist) survive reruns.
- **Publication is whole-entry and human.** Block publishing any shared entry carrying draft changes outside your fields and name the fields. Refuse to modify or publish archived entries, and refuse to overwrite an entry with a published version. Content that must never be published is made structurally unnameable by the publish phase, not noted in a runbook.
- **No deletion path** unless deletion is the task. Then: environment guard plus a uniquely named `--confirm-delete-...` flag, proofs that replacement content matches in every locale, no remaining or archived entries. Never delete content types to free capacity; capacity is the client's decision.
- **Locales are data.** Resolve the default locale from the API and fail if you cannot. Verify per locale, never on a union or from the default locale alone. Use Contentful's configured fallback, never an application-owned fallback or invented translation.
- **Env files are Jake's.** Override only the running process (`env NEXT_PUBLIC_CONTENTFUL_ENV=<sandbox> yarn ...`). Load credentials without printing them and redact `CFPAT-...` and `Bearer ...` from every error.
- **Verify by readback, UI, and rendered site.** Post-apply readback inside the tooling; re-plan to zero; screenshots per item type showing fields, labels, help text, and visibility; the real page loading from the migrated environment; page-by-page, locale-by-locale comparison against production where content moved. Distinguish file-backed evidence from what was observed live.
- **Migration scripts are artifacts.** House norm: schema goes forward by a human through Contentful's UI compare and merge tool. Scripts stay local and out of the production PR unless the repo says otherwise (worldpay's `scripts/contentful/contact-flow/` is committed by decision). Remove backward-compatibility code and fields as you go; slices must stay readable.
- **Report the write scope** every time: which space and environment were written, which were only read, which commands were never invoked.

## Workflow

Each step ends when its criterion is met.

1. **Ready the tooling.** Unit suite and typecheck green, guard proven by running a plan against `master` and showing the refusal. Tell Jake what admin action is needed next.
2. **Jake creates the environment.** Clone source named explicitly and resolved to a concrete id immediately before. Preflight that the target id does not already exist; the specified-id endpoint doubles as an update. Capture a source manifest (content-type, entry, asset, locale counts, default locale, target content-type definition and version).
3. **Confirm readiness independently.** CMA-read the target until `sys.status.sys.id === "ready"`. The CLI exit code and its "created" message prove nothing. After any timeout, read state before doing anything else; never issue repeated creates. Diff the target manifest against the source. If the build reads the environment by id, the Delivery and Preview API keys need it ticked under Settings, API keys, Environments; that is Jake's click.
4. **Preflight, read-only.** Resolve the environment id from the API and compare it to the intended target. Read content types, locales with fallbacks, editor interfaces (help text lives there), app installations (visibility rules live there), and the entries in scope. Confirm content-type capacity.
5. **Plan the migration.** Present operation counts and every blocker verbatim. Stop.
6. **Apply the migration** with `--apply`, target repeated in flags and variables, one command at a time with Jake validating between commands. Expect the readback line and the preservation count for shared configuration. Re-plan: `Planned operations: none`.
7. **Seed as drafts.** Plan, review the posture block, apply, re-plan to zero. Jake reviews the drafts in the UI.
8. **Publish, separately.** Plan, review, authorize, apply. Then the read-only verify, output captured to an evidence file.
9. **Build and exercise.** Full build against the environment (a migration can succeed while the build 404s on key scoping), typecheck, tests, real pages, a real submission with every outbound side-effect kill switch on in every deploy context.
10. **Destructive cleanup last, if in scope.** Dry run, then `--apply` plus the confirm flag, gated on per-locale proofs. Re-plan to confirm absence.
11. **If anything was fixed mid-sequence, the sandbox is spent.** Jake deletes and re-clones it; re-run from step 4. A sandbox that already holds the end state cannot prove the script produced it.
12. **Hand Jake the cutover.** For a scripted production path: fork master, free slots, migrate the fork with a reviewed-plan `sha256:` binding, validate, build, then the alias flip, which is also the rollback. After the flip, unset any target override and re-plan against the alias expecting zero operations. Record per phase and per environment what was applied; three weeks later nobody remembers.
13. **Commit, push, message only on his word.** Leave changes uncommitted for review, run an independent adversarial review, then ask. Draft Slack messages and PR bodies; do not send.

## References

- [references/guards.md](references/guards.md): the guard shapes and refusal text from `safety.js` and the product-finder helpers.
- [references/cli-and-gotchas.md](references/cli-and-gotchas.md): contentful-cli and contentful-migration semantics, aliases, clones, defaults, locales, `UNRESOLVABLE_LINK`, key scoping, capacity.
- [references/incidents.md](references/incidents.md): what went wrong before, dated, with the lesson each one left.
- [references/repos.md](references/repos.md): per-repo variable names, scripts, spaces, and the docs to read first.
