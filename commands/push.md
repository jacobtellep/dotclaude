---
description: Safe push - pulls from remote first, then pushes
allowed-tools: Bash
---

# Safe Push

Push changes to remote with pull-first strategy to avoid conflicts.

## Instructions

### 1. Pre-flight Checks

Run these checks before pushing:

```bash
git branch --show-current
git status --short
git remote -v
```

**Verify**:
- You're on a named branch (not detached HEAD)
- Note any uncommitted changes and warn the user
- Remote exists (typically `origin`)

### 2. Get Current Branch

```bash
BRANCH=$(git branch --show-current)
```

If on detached HEAD, stop and inform the user they need to be on a branch.

### 3. Check for Uncommitted Changes

If there are uncommitted changes:
- Warn the user: "You have uncommitted changes. These will not be pushed."
- Ask if they want to continue or commit first (suggest using `/commit`)

### 4. Pull from Remote

Sync with remote before pushing:

```bash
git pull origin <branch>
```

**If pull fails due to conflicts**:
- List the conflicting files
- Stop and inform the user: "Merge conflicts detected. Please resolve them before pushing."
- Show which files have conflicts
- Do NOT attempt to auto-resolve

**If pull succeeds**:
- Report any new commits that were pulled
- Continue to push

### 5. Push to Remote

```bash
git push origin <branch>
```

**If no upstream is set** (first push of a new branch):
```bash
git push -u origin <branch>
```

### 6. Report Results

After successful push:
- Confirm success with branch name
- Show the remote URL if available
- Report how many commits were pushed

If push fails:
- Show the error message
- Suggest possible fixes (e.g., force push if intentional, or pull again)

## Safety Rules

- Never use `--force` or `--force-with-lease` unless explicitly requested
- Never push to `main` or `master` with force
- Always pull before pushing
- Stop on merge conflicts - let the user resolve them
