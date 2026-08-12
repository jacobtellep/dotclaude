---
name: wt-report
description: Survey every git worktree for installed dependencies and build output, then strip, archive, or remove the ones the user picks. Use when reclaiming disk space, auditing which worktrees exist and what they cost, or clearing up after agentic work left worktrees and duplicated node_modules behind.
user-invocable: true
allowed-tools: Bash, AskUserQuestion
---

# Worktree Report

Agentic work leaves worktrees behind, each carrying its own copy of `node_modules`. This surveys all of them, then acts only on what the user picks.

Report first, act second. Never delete anything before the user has seen the report and chosen.

## Step 1 — Discover

Derive worktrees from git, not from a hardcoded path list, so new tooling areas are picked up automatically.

For every repo directory in `~/projects/*/` that has a `.git`, run:

```bash
git -C <repo> worktree list --porcelain
```

Collect every `worktree` path. Then:

- **Drop the main worktree** of each repo — the entry whose path is the repo root itself. This skill only ever touches linked worktrees.
- **Split registered-but-missing** paths into a separate "stale registration" list (the directory no longer exists).

Known areas these land in, for grouping the report: `~/projects/worktrees/` (the `/wt` skill), `~/.codex/worktrees/`, `/private/tmp/`, `/private/tmp/claude-501/` (Claude Code's own, usually self-cleaning), `~/.treehouse/`.

## Step 2 — Measure

For each live linked worktree, size these two categories separately with `du -sk`:

- **Dependencies** — `node_modules`, `.venv`, `venv`, `vendor`, `target`, `Pods`, `.yarn/cache`
- **Build output** — `.next`, `.turbo`, `dist`, `build`, `out`, `.cache`, `.parcel-cache`, `.svelte-kit`, `coverage`

Only at the worktree root and one level below a workspace package directory. Do not walk the whole tree.

**Before counting a build-output directory, confirm git ignores it:** `git -C <worktree> check-ignore -q <dir>`. A tracked `dist` or `build` is source, not output — exclude it from the report entirely.

## Step 3 — Assess safety

For each worktree, gather the facts that decide whether removal is safe:

```bash
git -C <worktree> status --porcelain          # empty = clean
git -C <worktree> branch --show-current
git -C <worktree> log --oneline @{u}..        # empty = nothing unpushed; fails = no upstream
git -C <worktree> log -1 --format=%cr         # how recently the branch was committed to
```

Classify each as:

- **safe** — clean tree, upstream exists, nothing unpushed
- **unpushed** — commits not on the remote, or no upstream at all
- **dirty** — uncommitted changes present

## Step 4 — Report

Group by area. Sort by total size, largest first. Number every row so the user can select by number.

```
~/projects/worktrees/ (your /wt skill)

  1. worldpay-com/fix-product-finder-error
     dependencies   1.02 GB  node_modules
     build output   340 MB   .next, .turbo
     last commit    6 days ago
     git state      safe — clean, pushed

  2. ample-co/cms-collapsed
     dependencies   0.94 GB  node_modules
     last commit    3 weeks ago
     git state      dirty — 4 uncommitted files
```

Close with totals: worktree count, total dependencies, total build output, and the combined figure that could be reclaimed. List stale registrations separately with a note that `git worktree prune` clears them.

## Step 5 — Choose what to strip

Ask which worktrees should have dependencies and build output deleted. Accept numbers, ranges, and `all`, for example `1-5, 8, 12`.

State plainly what stripping costs: the worktree stays checked out and registered, and the next use needs a fresh install. Any dev server running there breaks.

Offer one shortcut: every worktree whose last commit is older than a month.

## Step 6 — Choose what to archive or remove

Ask separately, on the same numbering.

**Archive** preserves the branch and reclaims the whole directory:

1. If the branch has unpushed commits or no upstream, run `git -C <worktree> bundle create ~/worktree-archive/<repo>-<branch>.bundle --all` first. Create `~/worktree-archive/` if needed.
2. `git -C <repo> worktree remove <path>`
3. Report where the branch survives — the remote, or the bundle path.

**Remove** discards the worktree without preserving anything. Offer it only for worktrees classified **safe**.

Two hard rules:

- A **dirty** worktree is never archived or removed until the user has seen the uncommitted file list and confirmed that specific worktree by name. Show the list; make them say it.
- Reach for `git worktree remove` and let it refuse. Use `--force` only after the user confirms that named worktree, and say what is being overridden.

## Step 7 — Execute

Work through the approved list one worktree at a time, printing each action as it happens.

Deleting a dependency directory goes through `rm -rf`, which the `rm_rf_guard` PreToolUse hook intercepts — expect an approval prompt per deletion and let the user answer it.

Finish with `git -C <repo> worktree prune` for every repo touched, plus any repo with stale registrations.

## Step 8 — Summary

```
Swept N worktrees

  Stripped     N worktrees, X.X GB reclaimed
  Archived     N worktrees, X.X GB reclaimed (branches at origin / bundles in ~/worktree-archive/)
  Removed      N worktrees, X.X GB reclaimed
  Pruned       N stale registrations
  Skipped      N (dirty or unpushed, listed with why)

  Total reclaimed: X.X GB
```

Name every skipped worktree and the reason, so nothing quietly stays behind.
