---
description: Smart commit - analyzes changes and creates logical commits with auto-generated messages
allowed-tools: Bash, Read, Glob
argument-hint: [message] or [--type TYPE] [--scope SCOPE] [message] or [contextual instructions]
---

# Smart Commit

Analyze all changes in the repository and create logical, well-structured commits with auto-generated conventional commit messages.

## Arguments

If arguments are provided via `$ARGUMENTS`, they can be used in three ways:

1. **Quick commit mode**: If a single conventional commit message is provided (e.g., `/commit "fix: resolve bug"`), use it directly for all staged changes

2. **Structured mode**: Parse `--type`, `--scope` flags to build a commit message (e.g., `/commit --type feat --scope auth "add login"`)

3. **Contextual instructions**: Provide natural language instructions to guide which changes to commit (e.g., `/commit only commit the changes related to the change we just finished`). These instructions are used to filter and select relevant files/changes before committing.

**No arguments**: Follow the full analysis workflow to create multiple logical commits

## Instructions

### 1. Check for Arguments

If `$ARGUMENTS` is provided, parse it in this order:

**Step 1a: Check for structured flags**
- Look for `--type TYPE` or `-t TYPE` flag
- Look for `--scope SCOPE` or `-s SCOPE` flag
- If flags are found, extract remaining text as description and construct message: `type(scope): description`
- Proceed to step 2 with the constructed message

**Step 1b: Check for complete conventional commit message**
- If `$ARGUMENTS` starts with a conventional commit type (`feat:`, `fix:`, `docs:`, etc.) or pattern (`type(scope):`), treat it as a complete commit message
- Use the message as-is
- Proceed to step 2 with the provided message

**Step 1c: Treat as contextual instructions**
- If neither flags nor conventional commit pattern detected, treat `$ARGUMENTS` as contextual instructions
- Store these instructions to guide file selection and commit message generation
- Continue to step 2, but use the contextual instructions to filter which changes to commit

**Usage examples:**
- `/commit "fix: resolve login bug"` → Use message directly for all staged changes
- `/commit --type feat --scope auth "add login functionality"` → Build `feat(auth): add login functionality`
- `/commit only commit the changes related to the change we just finished` → Use contextual instructions to filter changes
- `/commit commit the authentication changes` → Use contextual instructions to find auth-related files

### 2. Gather Context

Run these commands to understand the current state:

```bash
git status
git diff
git diff --cached
git log --oneline -5
```

If contextual instructions were provided in step 1c, also review:
- Recent conversation context (if available) to understand what "we just finished"
- File paths and content to match against the contextual instructions
- Related files that might be part of the same change

### 3. Analyze Changes

**If contextual instructions were provided:**
- Filter files/changes based on the contextual instructions
- Match file paths, content, and changes against the context (e.g., "changes related to the change we just finished")
- Only include files that are relevant to the contextual instructions
- If the context mentions specific features/modules, prioritize those files
- Generate commit message based on the filtered changes and contextual instructions

**If no contextual instructions (or structured message provided):**
Review all modified, staged, and untracked files. Group them into logical commits based on:

- **Feature work**: New functionality or enhancements
- **Bug fixes**: Corrections to existing behavior
- **Refactoring**: Code restructuring without behavior changes
- **Documentation**: README, comments, docs updates
- **Configuration**: Config files, dependencies, build settings
- **Tests**: New or updated tests
- **Styling**: Formatting, whitespace, linting fixes

Keep related changes together. For example:
- A new component and its tests = one commit
- Package.json changes with lock file = one commit
- Unrelated config changes = separate from feature work

### 4. Generate Commit Messages

**If a commit message was already provided** (from step 1a or 1b), use it as-is.

**If contextual instructions were provided** (from step 1c):
- Analyze the filtered changes to determine the appropriate commit type and scope
- Incorporate the contextual instructions into the description when relevant
- Use conventional commits format: `type(scope): description`

**Otherwise**, use conventional commits format: `type(scope): description`

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting, no code change
- `refactor` - Code restructuring
- `test` - Adding/updating tests
- `chore` - Maintenance, dependencies, config

**Scope**: Derive from the primary file path or module (e.g., `auth`, `api`, `ui`, `config`)

**Description**:
- Use imperative mood ("add" not "added")
- Be concise but descriptive
- Focus on the "why" when relevant
- If contextual instructions provide context, incorporate it naturally into the description

### 5. Create Commits

**If contextual instructions were provided:**
- Stage only the files that match the contextual filter: `git add <filtered-files>`
- Create a single commit with the generated message
- Leave other unrelated changes unstaged

**Otherwise**, for each logical group:

1. Stage the relevant files: `git add <files>`
2. Create the commit with the generated message
3. Use HEREDOC format for multi-line messages if needed:
   ```bash
   git commit -m "$(cat <<'EOF'
   type(scope): short description

   Optional longer description if needed.
   EOF
   )"
   ```

### 6. Report Results

After completing all commits:
- List all commits created with their messages
- Show `git log --oneline -n <number of new commits>`
- If contextual instructions were used, explain which files were included and why
- Note any files intentionally left uncommitted (especially if contextual filtering excluded them)

## Safety Rules

- Never commit files that appear to contain secrets (.env, credentials, API keys)
- Warn if committing large binary files
- Skip empty commits
- Respect .gitignore
