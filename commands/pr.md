---
description: Create PR against parent branch, then open in browser
allowed-tools: Bash
---

# Create Pull Request

Create a GitHub pull request against the repository's default branch using `gh`.

## Instructions

### 1. Pre-flight Checks

Run these checks first:

```bash
git rev-parse --is-inside-work-tree
git branch --show-current
```

**Verify**:
- You're inside a git repository
- You're on a named branch (not detached HEAD)
- You're NOT on `main` or `master` (can't PR to itself)

If on `main` or `master`, stop and inform: "You're on the default branch. Create a feature branch first."

### 2. Detect Base Branch

Get the repository's default branch:

```bash
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
```

Store this as the base branch for the PR.

### 3. Check for Existing PR

Check if a PR already exists for this branch:

```bash
gh pr view --json url 2>/dev/null
```

**If PR exists**:
- Inform the user: "A PR already exists for this branch"
- Open it in browser: `gh pr view --web`
- Stop here

### 4. Check Remote & Push

Check if branch exists on remote:

```bash
git ls-remote --heads origin $(git branch --show-current)
```

**If not on remote**:
- Push with upstream tracking: `git push -u origin <branch>`
- Report that branch was pushed

### 5. Verify Commits Ahead

Check there are commits ahead of base:

```bash
git rev-list --count <base-branch>..HEAD
```

**If zero commits**:
- Stop and inform: "No commits ahead of <base-branch>. Nothing to PR."

### 6. Gather Context

Show the user what will be in the PR:

```bash
git log --oneline <base-branch>..HEAD
```

### 7. Check for PR Template

Look for a PR template in the repo:

```bash
cat .github/pull_request_template.md 2>/dev/null
```

If a template exists, use it as the body structure and fill in the sections based on the commit context gathered in step 6. If no template exists, use a default body:

```
## Summary
<!-- Brief description of changes -->

## Changes
-

## Testing
-
```

### 8. Create PR

Create the pull request (without `--web` — create it first, open after):

```bash
gh pr create --base <base-branch> --fill --body "<filled-body>"
```

The `--fill` flag auto-generates the title from commit messages.

### 9. Open in Browser

After the PR is created, open it in the browser:

```bash
gh pr view --web
```

### 10. Report Results

After successful creation:
- Confirm PR was created with a link to the URL
- Note that it was opened in browser for review

## Safety Rules

- Never create PR from main/master to itself
- Always check for existing PR first
- Verify there are commits to include
- Auto-push if branch not on remote
