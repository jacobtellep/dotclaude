---
name: check-code
description: Run the project's lint, typecheck, and test scripts (non-interactively, with timeouts) and report a machine-readable VERIFY line. Use before claiming code works or is fixed, before any commit/push/PR, or when asked "does it pass" or "run the checks".
argument-hint: "[--only lint,typecheck,test] [--refresh-baseline]"
---

# check-code — lint / typecheck / test gate

**Never report implementation work as done without a fresh `VERIFY:` line from this skill.**

Part of the `/checks` family. You drive the project's own scripts directly with the Bash tool — there is no wrapper script. Three non-negotiables:

1. Every command is **non-interactive** (no watch mode, no prompts).
2. Every command has a **timeout**.
3. The report ends with a **`VERIFY:` line** (the evidence skill consumes it).

## 1. Discover the commands

Read `package.json` — in a monorepo, the changed workspace package's, and run from that package's root. Resolve:

- **Package manager** from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, `bun.lock(b)` → bun, else npm. (This repo family: always yarn.)
- **lint**: the `lint` script, else `SKIP(no script)`.
- **typecheck**: first of `typecheck` / `type-check` / `tsc` / `check-types`; else `npx --no-install tsc --noEmit` if a `tsconfig.json` exists; else `SKIP(no tsconfig)`.
- **test**: prefer a CI-safe variant (`test:ci`, `test:unit`) over `test`. **Read the resolved script body before running it** — that's how you catch the traps below.

If `$ARGUMENTS` has `--only`, run just those checks and mark the rest `SKIP(--only)`.

## 2. The watch-mode trap

`CI=true` is **not** enough: explicit CLI flags in the script body beat env vars (`"test": "jest --watch"` will hang forever regardless of env). Before running, scan the resolved command and fix:

| Script body contains | Run instead |
|---|---|
| `jest --watch` / `jest --watchAll` | `test:ci` script if present, else append `--ci --watchAll=false` (later flags win) |
| `vitest` without `run` | `vitest run` |
| any `--watch` / `-w` / `--interactive` | strip or override it |
| `next dev`, `serve`, `start` masquerading as a check | don't run it — that's a server, not a check |

Still export `CI=true` on every command (kills prompts, enables CI reporters) — belt and braces, not the safety mechanism.

## 3. Run

The three checks are independent — run them as parallel Bash calls. For each:

- Set the Bash `timeout` parameter: 300000 ms default; raise it for known-slow suites, never remove it.
- Keep full output as evidence, short output in context:

  ```bash
  LOG=~/.cache/agent-evidence/$(basename "$PWD")/$(date +%Y%m%d-%H%M%S) && mkdir -p "$LOG"
  CI=true yarn test:ci > "$LOG/test.log" 2>&1; echo "exit=$?"; tail -30 "$LOG/test.log"
  ```

- **A timeout is a hang, not a slow pass.** If a command times out, find the interactive flag you missed, fix the invocation, and re-run — never report a timed-out check as anything but FAIL(hung).

## 4. Report

End with one line, counts pulled from the actual output:

```
VERIFY: lint=PASS typecheck=FAIL(3) test=PASS logs=<log dir>
```

- On any FAIL: read the full log, fix the failures, re-run. Repeat until PASS or genuinely blocked — then report the failure honestly with the log excerpt.
- On SKIP: say so plainly. Do not invent substitute commands or imply the check passed.
- **Pre-existing failures (baseline cache)**: noisy repos (hundreds of lint/type errors already on `main`) otherwise cost a full baseline re-derivation every run. Cache it once per repo+base:

  ```bash
  BASE=$(git merge-base "${BASE_BRANCH:-main}" HEAD)
  BCACHE=~/.cache/agent-evidence/$(basename "$PWD")/baseline-${BASE_BRANCH:-main}.txt
  # file holds: <base-sha> lint=<n> typecheck=<n> test=<n>
  ```

  On each run: if `$BCACHE` exists and its stored SHA equals the current `$BASE`, diff today's counts against it and report only the **delta you introduced** (`typecheck=FAIL(2 new; 22 baseline)`). If the file is missing, its SHA is stale, or `$ARGUMENTS` has `--refresh-baseline`, regenerate it from a clean run on `$BASE` (`git stash` or checkout the base commit), then write the new counts + SHA. You own new failures; never silently absorb or "fix" pre-existing ones. When genuinely unsure and no cache exists, fall back to a one-off `git stash` baseline run.

## Red-green proof (when you wrote a regression test)

A test that cannot fail proves nothing. If this task added a test for the fix:

1. Run the test — it passes.
2. Revert the fix only (stash or comment out) — run the test — it MUST fail.
3. Restore the fix — run the test — it passes again.

If step 2 doesn't fail, the test is theater: rewrite it before claiming done.

## Hand-off

- Change touches anything user-visible (components, styles, markup)? → use the **check-ui** skill next.
- Always end the task with the **evidence** skill's Evidence block.
