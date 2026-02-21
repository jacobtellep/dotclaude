---
name: wt
description: "Create a git worktree with a new branch off a target branch, copying env files."
user-invocable: true
disable-model-invocation: true
argument-hint: "<new-branch> <target-branch>"
allowed-tools: Bash, Read, Glob, AskUserQuestion
---

# Git Worktree Creator

Create a git worktree with a new branch based on a target branch, copying env files automatically.

## Instructions

### Argument Parsing

Parse `$ARGUMENTS` by splitting on whitespace:
- First token = `NEW_BRANCH`
- Second token = `TARGET_BRANCH`
- If either is missing, use AskUserQuestion to prompt for the missing value(s)

### Step 1 — Validate git repo

Run `git rev-parse --is-inside-work-tree`. If this fails, tell the user they must be inside a git repository and stop.

### Step 2 — Determine repo name

1. Try: parse repo name from `git remote get-url origin` — extract the last path segment and strip the `.git` suffix
2. Fallback: `basename "$(git rev-parse --show-toplevel)"`

Store as `REPO_NAME`.

### Step 3 — Find main repo root

Handle being invoked from inside an existing worktree:

1. Run `git rev-parse --git-common-dir`
2. If the result is just `.git`, then `MAIN_REPO_ROOT=$(git rev-parse --show-toplevel)`
3. If it's an absolute path containing `.git/worktrees/`, strip everything from `.git/worktrees/` onward to get the main repo root
4. Otherwise, resolve the path to its parent directory

Store as `MAIN_REPO_ROOT`.

### Step 4 — Fetch latest

1. Check if an `origin` remote exists: `git remote | grep -q origin`
2. If yes: run `git fetch origin`
3. If no: warn the user that no `origin` remote was found and that only local refs will be used. Set a flag `HAS_REMOTE=false`.

### Step 5 — Branch conflict check

Check if `NEW_BRANCH` already exists:
- `git branch --list "$NEW_BRANCH"` (local)
- `git branch -r --list "origin/$NEW_BRANCH"` (remote, only if `HAS_REMOTE`)

If the branch exists, use AskUserQuestion with these options:
1. **Use existing branch** — create worktree using the existing branch
2. **Pick a new name** — prompt for a different branch name
3. **Abort** — stop execution

Track whether we're using an existing branch via `USE_EXISTING_BRANCH`.

### Step 6 — Verify target branch exists

Verify the target branch ref exists:
- If `HAS_REMOTE`: `git rev-parse --verify "origin/$TARGET_BRANCH"`
- Otherwise: `git rev-parse --verify "$TARGET_BRANCH"`

If not found, tell the user the target branch doesn't exist and stop.

### Step 7 — Build worktree path

1. Sanitize `NEW_BRANCH`: replace `/` with `-`, strip any leading or trailing `-` characters
2. Construct path: `~/projects/<REPO_NAME>-<SANITIZED_BRANCH>`

Store as `WORKTREE_PATH`.

### Step 8 — Directory conflict check

Check if `WORKTREE_PATH` already exists. If it does, use AskUserQuestion with these options:
1. **Rename** — prompt for a different directory name
2. **Remove and prune** — remove the existing directory, run `git worktree prune`, then continue
3. **Abort** — stop execution

### Step 9 — Create worktree

Run the appropriate command:
- **New branch with remote**: `git worktree add <WORKTREE_PATH> -b <NEW_BRANCH> origin/<TARGET_BRANCH>`
- **New branch without remote**: `git worktree add <WORKTREE_PATH> -b <NEW_BRANCH> <TARGET_BRANCH>`
- **Existing branch**: `git worktree add <WORKTREE_PATH> <NEW_BRANCH>`

If the command fails, report the error and stop.

### Step 10 — Copy env files

1. Use Glob to find `.env*` files at `MAIN_REPO_ROOT` root level only (pattern: `.env*`, not recursive)
2. For each matched file, `cp` it to `WORKTREE_PATH`
3. Track how many were copied and their names
4. If none found, note that no env files were found to copy

### Step 11 — Print summary

Output the following summary:

```
Worktree created successfully!

  Branch:      <NEW_BRANCH>
  Based on:    <TARGET_BRANCH>
  Path:        <WORKTREE_PATH>
  Env files:   N copied (<comma-separated list of filenames, or "none found">)
```

Do not perform any additional post-setup actions.
