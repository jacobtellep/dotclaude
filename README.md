# dotclaude

This is my live `~/.claude` directory under version control: the skills, hooks, settings, and global instructions behind my Claude Code setup.
I wrote this README for peers who ask about my workflow.
The usage numbers in here come from mining my actual session logs (5,600+ prompts, 433 session transcripts), not from what I aspire to use.

## The one-line version

I run Claude Code like a managed team, not a chatbot.
Agents build in parallel worktrees, verify their own work in a real browser, and hand me evidence.
I stay in the loop as the final verification gate: agents in my setup are not allowed to say "done," only "awaiting acceptance."

## Operating principles (from [CLAUDE.md](CLAUDE.md))

- **High autonomy, hard gates.** Agents make the calls and fix what is broken, but never claim completion without fresh proof.
- **"Should work" is banned.** Every completion report ends with an Evidence block, including a mandatory never-empty "NOT verified" line that scopes what still needs human or deploy-time eyes.
- **No human effort-cost intuition.** Agents write far faster than I do, so the real cost of doing it right is low. The quality bar does not bend to "that is a lot of work."
- **Anti-slop.** No placeholder or stub code in real paths, no unrequested complexity, no fake fallbacks. Simplicity is a quality goal, not a shortcut.
- **Output is input, not truth.** This applies to subagents, to external model teammates, and honestly to me.

## How a task flows

1. **Kick off.** `/goal` pins a session objective for quick work. Bigger asks go through `/work`, which sizes the task against a checklist (none / lite / full spec) and routes it. Unclear intent goes to `/interview` first.
2. **Spec if warranted.** The `spec` skill writes reconciler-style specs modeled on Kubernetes: I own the Desired State (ensure-statements, observable checks), agents append observed Status. Any fresh session can resume any task from the spec plus fresh observation alone. This has survived real crashes: crews have died mid-task and resumed losslessly.
3. **Build in parallel.** `/wt` spins up git worktrees (env files copied, deps installed). Roughly 30% of my prompts come from worktree paths, often with several sessions running at once across Claude, Codex, and Cursor.
4. **Verify.** `/checks` diffs against the merge-base and routes: any code change to `check-code` (lint/typecheck/tests, non-interactive, everything under timeout), UI-touching changes additionally to `check-ui` (a real browser with hard assertions, not eyeballing). The skills talk to each other through machine-readable `VERIFY:` and `VERIFY-UI:` lines.
5. **Evidence.** The `evidence` skill is the terminal gate: a claims-to-proof table, a list of pre-rejected rationalizations ("I'm confident" is not evidence), and the Evidence block format.
6. **I accept.** For full-tier work, a fresh-context subagent first runs a refutation pass: given only the spec and the diff (never the implementer's reasoning), it tries to prove each criterion NOT met. Then I do a short guided acceptance pass generated from the spec's ensure-list. Only after that do we `/commit` and `/push`.

## The skill families

### Verification loop (the most-exercised family, by the data)

`checks` → `check-code` + `check-ui` → `evidence`.
Highlights worth stealing:

- **Typed text interfaces.** Skills compose through machine-readable lines (`VERIFY: lint=PASS typecheck=FAIL(3) test=PASS`), not shared state.
- **Baseline-delta cache.** In noisy repos, check-code caches the merge-base's failures so reports show only the delta the agent introduced (`typecheck=FAIL(2 new; 22 baseline)`).
- **Red-green proof.** Any regression test must be shown failing with the fix reverted, or "the test is theater."
- **Assertion grammar in check-ui.** Every verdict field must name its proving mechanism (`hover=getComputedStyle Δconfirmed(#333→#fff)`). If the verdict reads like something you could write without opening a browser, you have not verified it.

### Task lifecycle

`work` (thin front-door router) → `interview` (deep AskUserQuestion interviews) → `spec` (reconciler specs) → `wt` (worktrees) → `done` (session capture to Obsidian).
The interview skill has an "educate-to-decide" ladder for when I answer "I don't know": first try to answer from the codebase, then present previewed options where every tradeoff claim must cite file:line evidence or be labeled an assumption.
The design spec behind this system lives at [specs/work-reconciler-v1.md](specs/work-reconciler-v1.md) and is itself a working instance of the format.

### Independent teammates

`braintrust` convenes the Cursor CLI and the OpenAI Codex CLI as an adversarial panel, with Claude as the driver.
Both run auto-mode and strictly read-only, with live web search.
The key rule: Claude forms its own provisional answer first, then dispatches the panel with a refute framing ("find the strongest reasons this is WRONG").
Never outsource the thinking; outsource the checking.
`cursor-research` and `codex-research` are the single-teammate versions for lighter cross-checks.
Missing subscriptions degrade gracefully but never silently.

### Communication and teaching

- `dm` drafts Slack messages in my voice (from a VOICE.md style file). Client-facing messages become drafts I send myself, which avoids Slack's "via Claude" badge; internal messages direct-send after I approve the text.
- `lavish` / `explain-changes` render rich interactive HTML explainers with an annotate-and-iterate feedback loop, for when I need to genuinely understand code I did not write.
- `educate` and `teach` exist because learning is part of my loop, not optional. I want to stay a better engineer than my agents' rubber stamp.

### Utilities

`diagnose` (feedback-loop-first debugging: build a deterministic pass/fail signal before hypothesizing), `improve` (read-only codebase audits that produce plans for cheaper executor models), `todoist-cli` (captures action items that need me specifically), `skill-developer`, `modern-web-guidance`, and a few others.
See the [skills/](skills/) directory; each has a self-describing SKILL.md.

## What I actually use (last 60 days)

Typed slash commands, top of the list:

| Command | Uses | What it tells you |
|---|---|---|
| `/compact` | 65 | I run long sessions and compact at natural boundaries |
| `/goal` | 32 | My current front door for pinning session objectives |
| `/model` | 31 | Quota-aware model routing is constant (Fable/Opus/Sonnet) |
| `/commit` | 23 | Commits are a deliberate ritual after I verify, not automatic |

Skill invocations by the agent itself: `check-code` (13), `evidence` (11), `work` (7), `spec` (7), `interview` (6), `todoist-cli` (5).
The verification family accounts for about a third of all skill invocations, so the "no Evidence block means not done" mandate is actually exercised, not aspirational.

I also prune on data: in July 2026 I retired about a third of my skill library (see [skills-retired/](skills-retired/)) based on 30-day zero-usage counts.
The retirement decision was itself recorded as a decision of record in the /work spec.

## The harness

- **SessionStart hooks** run three self-describing "agent experience" CLIs whose usage output lands directly in session context: `gh-axi` (GitHub operations), `chrome-devtools-axi` (browser automation from Bash, no MCP schema overhead), and `lavish-axi` (interactive HTML review surfaces). All are npm packages built for agents rather than humans: token-dense, machine-parseable, pipeable.
- **PreToolUse hook** ([hooks/pre_tool_use.py](hooks/pre_tool_use.py)) is a small Bash safety gate: blocks `chmod 777` and raw-disk `dd`, warns on `.env` access.
- **Plugins:** codex (OpenAI Codex integration), chrome-devtools-mcp, code-simplifier, frontend-design.
- **Voice and opinions files** (`~/OPINIONS.md`, `~/VOICE.md`, not in this repo): curated stances and writing style that agents read on demand. Curated files win over auto-memory on conflict.
- **[bin/ralph.sh](bin/ralph.sh):** an overnight agent loop with a verification reject-gate. Each iteration feeds a prompt file plus prior failure logs to a headless agent under a timeout, then a verify script decides pass, retry, or stuck.
- **Statusline** ([statusline.sh](statusline.sh)): repo, branch, and time since last commit.

## Multi-model workflow

Beyond the braintrust skill, cross-model adversarial review is a standing habit: Claude and Codex review the same PR with fresh context in separate doc directories, then consolidate and validate each other's findings.
I route work by quota deliberately: Sonnet subagents and Codex for mechanical work to stretch Fable 5 usage, and I sometimes run Claude Code sessions inside Codex-created worktrees.
"Fan out subagents" is probably my most-typed phrase, always with one orchestrator (or me) as the final decision maker.

## Repo layout

Tracked: `CLAUDE.md`, `settings.json`, `skills/`, `commands/`, `hooks/`, `bin/`, `specs/`, `statusline.sh`, `skills-retired/`.
Gitignored: session transcripts, caches, plugin downloads, logs, and machine-specific state (see [.gitignore](.gitignore)).
Caveat: some skills are symlinks into `~/.agents/skills/`, a shared skills directory outside this repo, so the symlinks restore but their content lives elsewhere.

## If you take one thing

Take the verification loop.
The single biggest change in my results came from making "done" mean something: machine-readable check results, a real browser for UI claims, and an Evidence block with an honest "NOT verified" line.
Everything else in this repo is compounding on top of that.

Let me know if you want a walkthrough of any piece.
