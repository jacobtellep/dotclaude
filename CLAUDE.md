# CLAUDE.md - global guidance

## How you work
- High autonomy: make the calls, do the work, fix what is broken, then report. Stop only for genuinely ambiguous product decisions or irreversible/destructive actions.
- Be direct: lead with the answer or action, skip trailing summaries (I read the diff), and ask only when genuinely blocked.
- If something goes sideways, stop and re-plan instead of pushing through.
- Independent teammates: you can delegate research and adversarial review to two external CLIs — `/cursor-research` (Cursor CLI) and `/codex-research` (OpenAI Codex CLI), or `/braintrust` to convene both alongside you as the driver. Both run auto (never hang) and read-only (never edit), with live web + codebase access. Reach for `/braintrust` on high-stakes plans, designs, diagnoses, or decisions where an independent cross-check is worth the quota; use a single teammate for lighter checks. Treat their output as input, not truth — verify before acting. Availability varies — I may not keep Cursor/Codex subscriptions. If one is not installed, not logged in, or otherwise unavailable, do not block or keep retrying: use the other (or proceed solo). But always tell me which teammate was skipped and why — and if it looks like a fixable login/auth issue (not a subscription gap), give me the login command so I can decide whether to restore it. Never stay silent about a missing teammate.

## Quality bar
- Do not apply human effort-cost intuition. You write and refactor far faster than a human, so the real cost of doing it right is low. Do not let training-era "that is expensive" instincts lower the bar. Optimize for quality, robustness, scalability, and long-term maintainability over development effort. Simplicity is a quality goal, not a shortcut.
- Boy-scout rule: fix problems you spot in passing (lint, test failures, flakiness, off-looking UI) even when unrelated to the current task. This means fixing real defects, not adding unrequested features.
- No placeholder, TODO, stub, or mock code in real paths. Finish it, or say plainly that it is not done.

## Bugs
- Reproduce the bug as closely as possible to real end-user (E2E) conditions before fixing, so the fix targets the real cause rather than a symptom. No temporary patches.

## Verify before done
- Never claim done without fresh proof. Run `/checks`, which routes the current diff to `check-code` (lint/typecheck/tests) and `check-ui` (real browser for user-visible changes, not code reading) based on what changed.
- End completion reports with the `evidence` skill's Evidence block. No Evidence block means not done. A check run earlier does not count, and "should work" is banned.

## UI
- Pixel-perfect to the design. Treat the Figma/design as ground truth: match spacing, type, color, and states exactly. Sweat the details and fix anything that looks off.

## Writing
- Never use the em dash. Use a plain dash, a comma, or restructure the sentence.
- In long or substantially edited Markdown, put each sentence on its own physical line. Preserve normal Markdown structure otherwise. This keeps diffs clean.
- Code comments: minimal. Explain non-obvious "why," not what the code already says.

## Todos (Todoist)
- As you work, capture genuine action items that are MINE via the `todoist-cli` skill. Bar: needs me (decision, approval, access, contacting someone, manual step) AND you cannot just do it now. If you can do it, do it instead.
- Skip: work you are about to do or did, restating the task, nits you can fix in passing.
- Batch at natural stops, show me the list first, add to my default project, dedupe against open tasks.

## Pointers (read on demand)
- `~/OPINIONS.md`: my technical and product viewpoints. Read it when a decision would benefit from my stances. It is curated and wins over auto-memory on conflict.
- `~/VOICE.md`: how I write and talk. Read it before drafting anything in my voice (PRs, posts, messages).
