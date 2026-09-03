# contentful-cli, contentful-migration, CMA and CDA gotchas

## Contents

- Aliases and master
- Environment lifecycle
- Content types and capacity
- Fields, defaults, editor interfaces
- Entries and publication
- Locales
- Delivery API behaviour
- CLI commands
- Wiring and deploy

## Aliases and master

- `master` is usually an alias, not a concrete environment. Resolve it to the concrete id immediately before a clone and pass that id explicitly as `--source`. The alias can be retargeted between preflight and the write.
- An alias named like your sandbox passes a naive environment-id check. Read `sys.aliasedEnvironment`.
- The alias flip is both the cutover and the rollback: point it back at the previous environment if anything goes wrong. It is Jake's action.
- Delivery and Preview API keys scoped to the `master` alias follow it automatically at cutover; only direct-by-id access to a fork needs the key's environment checkbox.
- `contentful-cli` context commands (`space use`, `environment use`) are a footgun: an environment-less command defaults to `master`. Pass `--space-id` and `--environment-id` on every command.
- `NEXT_PUBLIC_CONTENTFUL_ENV` defaults to `master` in SibcyClineWebsite and clarkschaeferconsulting-com; the Crossroads Ruby framework's `CONTENTFUL_ENV` also defaults to `master`. Any tool that reads these without a guard targets production when the variable is unset.

## Environment lifecycle

- Creation is asynchronous: `queued`, `inProgress`, `ready`, `failed`. The contentful-cli `create` implementation only logs on `failed` and only logs not-ready after a timeout; neither throws. The exit code and the "created" message are not proof. CMA-read the target and require `sys.status.sys.id === "ready"`.
- A create can succeed server-side while the client times out. After any ambiguous response, read the target before doing anything else; never issue blind repeated creates.
- `PUT /spaces/<id>/environments/<envId>` doubles as an update when a version is supplied. If the target already exists, abort; do not update, delete, or treat it as success.
- No clone-lineage field exists on the target. The defensible proof of source is the captured concrete source id, the explicit `--source`, and a source-versus-target manifest recorded around creation.
- A clone brings the source's unpublished drafts with it. A shared Dictionary entry arrived with draft-only keys in unrelated fields and blocked publication until an editor cleared them. Warn about this in the clone section of the runbook, where it can be prevented.
- Cloning copies entries, assets, content types, locales, editor interfaces, extensions, app installations, releases, scheduled actions. Workflows are not copied. Memberships, roles, API keys, and webhooks are space-scoped.
- Documented limits: environment id max 40 characters, 151 environments per space, 12 creations per five minutes; plan entitlement can be lower. Display names are visible to anyone who can list environments.
- The same environment id can exist independently in two spaces.
- Deleting an environment is a separate destructive approval after re-verifying the exact space and environment id. Never delete another environment to make room.
- Clone from the environment that best resembles production at launch, not from the biggest or newest one (worldpay clones `contact-flow` from `wp-dev-test`, the one environment below the content-type cap with the needed free slots).
- Clone and verify one space at a time.

## Content types and capacity

- Content types are capped per space (75 in the Worldpay space; `master` sat at the cap). A migration that creates types refuses until slots are free, and that refusal is expected behaviour, not a broken command.
- Contentful refuses to delete a content type that still has entries, archived ones included. Entries go first. Freeing a slot is a client content decision, never an agent action.
- Requesting an unknown content type from the CDA returns 400 (`unknownContentType`), so any build step that queries by type makes the content-model migration a hard prerequisite of the code deploy.
- Old code plus new content is a distinct hazard: `withoutUnresolvableLinks` protects against missing entries, not against a present entry of a type the deployed code has no component for; it falls through the block registry.
- Two sibling sites can be two separate spaces (Clark Schaefer Consulting `45fgz00aw4jj`, Hackett `fldcb3509v6k`): two migrations, two sandboxes, two verifications.

## Fields, defaults, editor interfaces

- A field `defaultValue` is applied on every entry creation, including through the CMA, and cannot be scoped to one value of a discriminator field. `marketoInstance` was stamped onto 15 of 24 seeded entries that had no business carrying it. Defaults are applied at creation only and never backfill existing entries.
- Contentful shows every field on every entry of a content type. A writable field that is never read saves, publishes, passes the build, and does nothing. Field visibility is a correctness control.
- Field-hiding rules live in a partner app installation's parameters (FlexFields), per environment, not on the content type. They must be read and written as part of the migration inventory. Installing a licensed app is an administrator action; plan for it with a named instruction instead of a 404 mid-apply.
- Help text lives on the editor interface, not the content type. A migration that only diffs content types misses reworded or deleted guidance.
- `contentful-migration` scripts: `async function(migration, { makeRequest })`. `migration.editContentType(...)` is declarative; locales, editor interfaces, and existence checks come from `makeRequest` GETs. Assert compatibility and skip a pre-existing field; never converge a divergent shape.
- The Crossroads Ruby framework (`crds-contentful-migrations`) has `RevertibleMigration` (declare `content_type_id`, get an automatic `down`) and `contentful_migrations:pending` to preview. Its `CONTENTFUL_ENV` defaults to `master`.

## Entries and publication

- Contentful publishes an entry whole. Publishing your field on a shared entry publishes every other unfinished draft change on it.
- Contentful has no native validation that blocks publishing an entry whose linked asset is unpublished. Field validations check presence and type, not the target's publish state. You cannot prevent this with configuration; handle it in the application.
- Contentful refuses to publish an entry whose required links are empty, which worldpay uses deliberately so a reference entry cannot be published even by hand. It reads as a defect to anyone who has not read the ADR; document it where the confused person will look.
- Archived entries count as entries for deletion purposes and block content-type deletion.
- `contentful space import` skip flags are what keep an import from silently rewriting the model, locales, or existing entries: `--skip-content-model --skip-locales --skip-content-publishing --skip-content-updates`. `contentful space export --include-drafts` snapshots before a change. Export dumps are large durable artifacts (multi-GiB zips seen); do not clean them up as scratch.

## Locales

- Never assume the default locale. The Worldpay space has 22 locales with default `en`, not `en-US`. Resolve from `/locales` and fail if you cannot.
- Writing a partial locale map replaces the whole map. `{ en: ... }` over `{ en: ..., en-GB: ... }` deletes `en-GB`. Merge.
- Auditing entries as a union across locales hides per-locale gaps: master had 16 linked products for `/en` and 27 for `/en-GB`; the union looked complete.
- An intentionally blank field in one locale is not a missing field. Comparing two environments in English only made them look identical while non-English form ids differed.
- Each locale has a `fallbackCode`. Use Contentful's fallback; do not add an application-level fallback language. Seeded English microcopy will render in English on a French form until the other locales are authored.
- A verify pass can legitimately report excluded locales. Locale coverage is data to check, not an error to fix silently.

## Delivery API behaviour

- The web app shows drafts; the Delivery API serves only published content. An asset that looks fine to a logged-in editor can be `null` for every visitor.
- GraphQL `UNRESOLVABLE_LINK`: HTTP 200 with complete usable data, the broken field set to `null`, and an entry in the top-level `errors` array. Code that throws on any `data.errors` turns a benign draft link into a 500. The errors array is not scoped to the failing part of the query, so one bad link in a fanned-out query poisons the response.
- The documented skip technique (`where: {sys: {id_exists: true}}`) only skips unresolvable links in a collection. Nothing suppresses a single-entity or asset link error on a field.
- Tolerate exactly `extensions.contentful.code === 'UNRESOLVABLE_LINK'`, log enough to find the entry, and keep every other code failing loudly. Fix it centrally in the fetch layer rather than per call site (SibcyClineWebsite `src/lib/cms/gql.js`). Do not fail the build on it; the outage never touched a build, and an editor's mistake should not block engineers shipping unrelated fixes.
- Verify publish state through the Delivery API, never by inference from a page that happens to render (the same query 500'd on one site and rendered on another against the same environment).

## CLI commands

- `contentful space environment create --space-id <s> --environment-id <e> --name <n> --source <concrete-id> --await-processing --processing-timeout <s>`, or the CMA `PUT` with `X-Contentful-Source-Environment`.
- `contentful space migration --space-id <s> --environment-id <e> <script.js>` for `contentful-migration` files.
- `contentful space export/import` as above; `contentful space environment list`, `contentful space environment-alias`.
- A management token acts with its user's permissions; creating or deleting a sandbox needs Space Administrator or manage-all-environments. It is a full-write credential for the whole space, which is why the environment guard lives in the tooling, not the credential.

## Wiring and deploy

- `NEXT_PUBLIC_CONTENTFUL_ENV` and its siblings are site-wide. Pointing an integration or production branch at a sandbox serves the entire site (redirects, navigation, dictionary, locales) from it and makes seeded test pages live. Rejected on worldpay for that reason; the smaller alternative was running only the migrate phase against master.
- The environment is usually set in two or three places (`.env`, `.envrc`, Netlify). direnv's `.envrc` export wins over `.env`. Enumerate all of them and report which one the running process resolved.
- A successful migration does not mean the site can read the environment. Delivery and Preview API keys are per-environment allowlists and return 404 for an environment not on the list. Only a real build catches it.
- Outbound side-effect kill switches (`CONTACT_FLOW_MARKETO_DRY_RUN=1`) must be set in every deploy context; Netlify previews run with `NODE_ENV=production`.
- Merge day and launch day have different env footprints: third-party credentials become build-required the moment the target environment has a published flow referencing them.
- Preview can resolve draft schemas at request time so an editor can exercise a never-published form (worldpay ADR 0004); by default a build-time snapshot means a never-published form cannot be previewed at all. Jake objects to designs that force a production publish just to preview.
