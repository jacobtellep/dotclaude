---
name: done
description: "Capture session context as a rich Obsidian-compatible markdown note"
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Glob, Grep
---

# Session Capture — `/done`

Synthesize the current session into a structured Obsidian note capturing decisions, knowledge, implementation details, and next steps.

## Constants

```
VAULT="/Users/jacobtellep/Library/Mobile Documents/iCloud~md~obsidian/Documents/OpenClaw"
```

## Step 1 — Determine project name

1. Get the current working directory
2. If `cwd` equals `$VAULT` (or is directly inside it with no sub-project), set `PROJECT_NAME` to `"general"`
3. Otherwise, derive `PROJECT_NAME` from `basename "$cwd"` — lowercase, replace spaces with hyphens, strip non-alphanumeric characters except hyphens

## Step 2 — Locate session transcript

1. Determine the project-specific transcript directory. Claude Code stores transcripts at:
   ```
   ~/.claude/projects/{sanitized-cwd-path}/
   ```
   where the sanitized path replaces `/` with `-` and prefixes with `-`. For example, `/Users/jacobtellep/myproject` becomes `-Users-jacobtellep-myproject`.

2. Find the most recent `.jsonl` file in that directory:
   ```bash
   ls -t ~/.claude/projects/{project-dir}/*.jsonl 2>/dev/null | head -1
   ```

3. If no transcript is found, proceed using only in-context memory (what you already know from this conversation).

## Step 3 — Gather session context

Use a combination of sources to understand what happened in this session. You already have the full conversation in context — that is your **primary source**.

If a transcript file was found, supplement with:
- Grep for user messages to catch anything from before context compression:
  ```bash
  grep -o '"type":"human"' "$TRANSCRIPT" | wc -l
  ```
- Read the last 200 lines for recent context:
  ```bash
  tail -200 "$TRANSCRIPT"
  ```

Also check:
- Read `TODO.md` in the project root if it exists (for task context)
- Read auto-memory files at `~/.claude/projects/{project-dir}/memory/MEMORY.md` if they exist

## Step 4 — Synthesize content

From all gathered context, synthesize content across these categories. **Omit any section that has no meaningful content.**

### Required sections:

1. **Summary** — 2-4 sentence overview of what was accomplished this session
2. **Decisions & Rationale** — Key choices made and why (architecture, library picks, approach changes)
3. **What Was Built / Changed** — Concrete deliverables: features added, files created/modified, bugs fixed
4. **Problems & Solutions** — Blockers encountered and how they were resolved
5. **Knowledge & Insights** — Patterns discovered, gotchas, things learned about the codebase or tools
6. **Next Steps / Open Questions** — What remains to be done, unresolved questions, follow-up items

### Technical appendix (bottom of note):

- **Files Changed** — bullet list of files created, modified, or deleted
- **Key Commands** — any notable commands used or that should be remembered
- **Code Snippets** — important code fragments worth preserving (use fenced code blocks)

Omit the technical appendix sections if empty.

## Step 5 — Generate metadata

1. **Topic slug**: Derive a 2-4 word kebab-case slug from the summary (e.g., `auth-flow-refactor`, `done-skill-creation`). Keep it descriptive and filesystem-safe.

2. **Tags**: Auto-generate 3-8 tags from the content. Always include `session-note`. Draw from:
   - Technologies used (e.g., `typescript`, `react`, `python`)
   - Type of work (e.g., `refactor`, `bugfix`, `feature`, `devops`, `planning`)
   - Project name
   - Domain concepts discussed

3. **Session ID**: Use the transcript filename (without extension) if available, otherwise `manual-{timestamp}`

## Step 6 — Scrub sensitive data

Before writing the note, scan all content for sensitive patterns and replace with `[REDACTED]`:
- API keys / tokens (patterns like `sk-`, `ghp_`, `Bearer ...`, `token: ...`)
- Passwords and secrets
- Private URLs with tokens/keys in query strings
- `.env` file values that look like credentials

## Step 7 — Check for existing note

Check if a note already exists for today's date in this project:
```bash
ls "${VAULT}/Sessions/${PROJECT_NAME}/$(date +%Y-%m-%d)"*.md 2>/dev/null
```

If found, you will overwrite it (same session, updated capture).

## Step 8 — Write the note

1. Create the directory if needed:
   ```bash
   mkdir -p "${VAULT}/Sessions/${PROJECT_NAME}"
   ```

2. Write the note to:
   ```
   ${VAULT}/Sessions/${PROJECT_NAME}/${YYYY-MM-DD}-${TOPIC_SLUG}.md
   ```

   If overwriting an existing note with a different slug, delete the old file first.

### Note Template

```markdown
---
date: YYYY-MM-DD
project: {PROJECT_NAME}
tags:
  - session-note
  - {tag1}
  - {tag2}
session-id: "{SESSION_ID}"
---

> [!info] Session Note
> **Date:** YYYY-MM-DD
> **Project:** {PROJECT_NAME}
> **Daily Note:** [[Daily Notes/YYYY-MM-DD]]

## Summary

{2-4 sentence overview}

## Decisions & Rationale

- **{Decision}** — {Why this choice was made}

## What Was Built / Changed

- {Concrete deliverable or change}

## Problems & Solutions

- **{Problem}** — {How it was resolved}

## Knowledge & Insights

- {Pattern, gotcha, or learning}

## Next Steps / Open Questions

- [ ] {Action item or open question}

---

## Files Changed

- `path/to/file` — {what changed}

## Key Commands

```bash
{notable command}
```

## Code Snippets

```{language}
{important code fragment}
```
```

## Step 9 — Display the note

After writing, display the **full note content** in the terminal so the user can review it immediately. Use a brief header like:

```
Session note saved to: {full path}
```

Then output the complete note content.

## Important Notes

- **Be thorough but concise** — capture what matters, skip noise
- **Prefer actionable content** — "we chose X because Y" over "we discussed X"
- **Use wiki-links** where natural — `[[concept]]` for Obsidian cross-referencing
- **Code snippets** should be the final/working version, not intermediate attempts
- **Next steps** should use checkbox syntax `- [ ]` for Obsidian task tracking
