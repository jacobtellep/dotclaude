---
name: migrate
description: Run DatoCMS migrations against a sandbox environment (HQ + Tennessee hub) in-place, then regenerate types
user-invocable: true
disable-model-invocation: true
argument-hint: "<environment-name>"
allowed-tools: Bash, Read, Edit, Grep
---

# DatoCMS Migration Runner

Run all pending DatoCMS migrations against a named sandbox environment **in-place** (no forking), for both the HQ project and the Tennessee hub (source of truth).

## Usage

```
/migrate <environment-name>
```

Example: `/migrate jt-components`

## Required Argument

`$ARGUMENTS` is the DatoCMS sandbox environment name (e.g., `jt-components`, `my-feature-branch`).

If `$ARGUMENTS` is empty, ask the user for the environment name before proceeding.

## Steps

### 1. Run HQ migrations

```bash
npx @datocms/cli migrations:run \
  --source=$ARGUMENTS \
  --in-place \
  --api-token=$DATOCMS_API_TOKEN
```

Uses the `DATOCMS_API_TOKEN` env var (HQ full-access token).

### 2. Run Tennessee hub migrations

**CRITICAL: The Tennessee token is stored in `.env.local`, NOT in the shell environment.** Before running the Tennessee migration, you MUST load the token from `.env.local` explicitly. Use this pattern:

```bash
DATOCMS_TOKEN_TENNESSEE=$(grep '^DATOCMS_TOKEN_TENNESSEE=' .env.local | cut -d'=' -f2) \
npx @datocms/cli migrations:run \
  --source=$ARGUMENTS \
  --in-place \
  --api-token=$DATOCMS_TOKEN_TENNESSEE
```

If `DATOCMS_TOKEN_TENNESSEE` is empty after loading, stop and tell the user to add it to `.env.local`.

Tennessee is the hub source of truth — Cincinnati and other hubs are derived from it.

### 3. Regenerate TypeScript types

After both migration runs succeed:

```bash
npx @datocms/cli schema:generate \
  --api-token=$DATOCMS_API_TOKEN \
  --environment=$ARGUMENTS \
  lib/datocms/types.ts
```

### 4. Update .env.local

Ensure the environment variables point at the sandbox:

- `DATOCMS_ENVIRONMENT=$ARGUMENTS` (for hub projects)
- `DATOCMS_ENVIRONMENT_HQ=$ARGUMENTS` (for HQ project)

Read `.env.local`, check if these are already set. If not, add or update them.

### 5. Report results

Summarize:
- How many migrations ran on HQ
- How many migrations ran on Tennessee
- Whether types were regenerated
- Whether `.env.local` was updated

## Error Handling

- If a migration fails, show the error and stop. Do not proceed to the next step.
- If an env var is missing (`DATOCMS_API_TOKEN` or `DATOCMS_TOKEN_TENNESSEE`), tell the user which token is missing and where to get it (DatoCMS project settings > API tokens).

## Notes

- Migrations are idempotent — they check if models exist before creating.
- The `--in-place` flag runs directly on the named environment without forking.
- Types file (`lib/datocms/types.ts`) is auto-generated and should not be manually edited.
