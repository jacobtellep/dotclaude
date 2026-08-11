---
name: asana-comments
description: Draft or post concise comments on specified Asana tasks in Jake's voice. Use when Jake explicitly asks to comment on, add a comment to, or leave a note on one or more Asana tasks; never infer a comment from a status change, and return a draft when no Asana connector is available.
user-invocable: true
disable-model-invocation: true
---

# Asana Comments

Jake supplies the tasks and intended facts. Keep the wording brief and the write boundary explicit.

## Write the comment

1. Use no more than two sentences unless Jake asks for more.
2. State the outcome or current truth, not process narration.
3. Use only facts Jake supplied or that are verified in the current task. You may add a relevant full PR or preview URL and minimal connective wording.
4. Omit agent, harness, worktree, or internal workflow terminology.
5. Use Jake's plain, direct register: no preamble, sign-off, exclamation point, em dash, "just," or unnecessary hedging.
6. Read `~/VOICE.md` before substantial or client-visible wording.
7. Never say "verified," "tested," "merged," or "done" without current evidence.

## Respect write intent

- Post only when Jake explicitly asked to add or leave the comment. A request to draft, rewrite, or review authorizes no Asana write.
- A status or section change does not imply a comment.
- Jake's explicit dictation is approval for the requested comment unless the wording introduces client-visible judgment not present in his request.
- When target task identity is ambiguous, resolve it before writing.

## Use the available connector

Discover and use the configured Asana MCP or app connector when available. Prefer plain text unless a real mention or task-link object requires rich text. Do not use browser automation to bypass a missing connector or authentication.

If no Asana write tool is available, return the exact post-ready comment and state that it was not posted. Do not imply success.

For a requested batch, perform the comments in one pass after resolving every target, then report one concise line per task with the actual result.
