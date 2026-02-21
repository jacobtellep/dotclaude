# Skill Spec: `/wt` — Git Worktree Creator

## Overview
A Claude Code skill that creates a new git branch off a specified target branch, sets up a git worktree for it in `~/projects/`, and copies all `.env*` files from the main repo root to the new worktree.

## Invocation
```
/wt <new-branch-name> <target-branch>
```
- **new-branch-name** (required if not provided, prompt): The name of the new branch to create. Used as-is — no prefix convention enforced.
- **target-branch** (required if not provided, prompt): The branch to base the new branch off of (e.g., `main`, `develop`).

If either argument is missing, the skill should prompt the user for the missing value(s) using `AskUserQuestion`.

## Behavior

### 1. Validation
- Confirm the current directory is inside a git repository.
- Determine the **repo name** from the git remote or directory name (e.g., `my-app`).
- Determine the **main repo root** (top-level git dir, not a worktree's root — use `git rev-parse --git-common-dir` to find the true root if invoked from a worktree).

### 2. Fetch Latest
- Always run `git fetch origin` before branching, to ensure the target branch ref is up to date with the remote.

### 3. Conflict Detection
- **Branch conflict**: If the branch name already exists locally or on the remote, ask the user what to do:
  - Pick a different name
  - Use the existing branch (checkout into worktree instead of creating)
  - Abort
- **Directory conflict**: If `~/projects/<repo-name>-<sanitized-branch>` already exists, ask the user:
  - Pick a different directory name
  - Remove existing directory and proceed
  - Abort

### 4. Branch + Worktree Creation
- Create the worktree directory at: `~/projects/<repo-name>-<sanitized-branch-name>`
  - Sanitize the branch name for filesystem use: replace `/` with `-`, strip leading/trailing dashes.
  - Example: repo `my-app`, branch `feature/auth-flow` → `~/projects/my-app-feature-auth-flow`
- Run: `git worktree add ~/projects/<dir-name> -b <new-branch-name> origin/<target-branch>`
  - This creates the branch and the worktree in one command.

### 5. Copy Environment Files
- Copy all files matching `.env*` from the **main repo root** (not the current worktree) to the new worktree directory.
  - Includes: `.env`, `.env.local`, `.env.development`, `.env.production`, `.env.test`, etc.
  - Uses glob: `.env*` at repo root level only (not recursive).

### 6. Output
- Print a success summary:
  - New branch name
  - Based on (target branch)
  - Worktree path
  - Number of env files copied (list their names)
- No additional post-setup actions (no install, no editor open, no cd).

## Skill Configuration

```yaml
---
name: wt
description: "Create a git worktree with a new branch off a target branch, copying env files. Use for worktree, new branch, git worktree add."
user-invocable: true
disable-model-invocation: true
argument-hint: "<new-branch> <target-branch>"
allowed-tools: Bash, Read, Glob, AskUserQuestion
---
```

## Edge Cases
- **Not a git repo**: Error with clear message.
- **No remote**: Warn but proceed (skip fetch, branch off local target).
- **No env files found**: Proceed normally, just note that no env files were found to copy.
- **Worktree already exists for branch**: Git will error — catch this and present options to the user.

## Directory Naming Examples

| Repo | Branch | Worktree Path |
|------|--------|--------------|
| `my-app` | `feature/auth` | `~/projects/my-app-feature-auth` |
| `my-app` | `fix-login-bug` | `~/projects/my-app-fix-login-bug` |
| `api-server` | `chore/deps` | `~/projects/api-server-chore-deps` |
| `web` | `main` | `~/projects/web-main` |
