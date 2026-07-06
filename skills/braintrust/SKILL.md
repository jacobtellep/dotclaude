---
name: braintrust
description: Convene an independent panel — the Cursor CLI and the OpenAI Codex CLI — alongside Claude Code as the main driver, to widen the surface area of adversarial reviews and research (both live web and the local codebase). Use when asked to "convene the braintrust", "get a panel", "adversarially review this", "stress-test with Cursor and Codex", or when a decision/plan/diagnosis is important enough to warrant multiple independent reasoners. Claude decides, at its discretion, how many teammates to use, which models, and whether to research the web, the codebase, or both. Composes the cursor-research and codex-research skills.
argument-hint: "<what to research, review, or stress-test> [+ optional focus, e.g. 'web only', 'adversarial', 'use opus + codex-high']"
---

# Braintrust

Claude Code is the **main driver**. This skill convenes two independent teammates — the **Cursor CLI** (`cursor-research`) and the **OpenAI Codex CLI** (`codex-research`) — to widen the surface area of a review or investigation, then Claude reconciles their input against its own analysis and delivers a single synthesized verdict.

The point is *independent coverage*. Three reasoners from different model families (Claude + Cursor's roster + OpenAI) catch failure modes that any one alone would miss. Use it when correctness matters more than speed.

## When to use

- **Adversarial review** — a plan, design, diagnosis, security assumption, or risky change you want genuinely stress-tested, not rubber-stamped.
- **High-stakes research** — a question worth answering from multiple independent angles, across the live web and/or the codebase.
- **Tie-breaking** — you and one teammate disagree, or you're uncertain and want convergence/divergence signal.

For routine questions, use a single teammate (`cursor-research` or `codex-research`) instead — the panel is heavier and spends more quota. Scale to the stakes.

## Prerequisites

Both underlying skills must be usable. Quick check (once per session):

```bash
which cursor-agent && cursor-agent status
which codex && codex login status
```

**Degrade gracefully, but never silently — availability is expected to vary.** The user may not always keep Cursor and/or Codex subscriptions. Treat each teammate as optional:
- If a CLI is missing, not logged in, or returns a subscription/entitlement error, continue with whoever remains — but **always report which teammate was skipped and the specific reason.**
- Distinguish a **fixable login/auth issue** (give the login command: `! cursor-agent login` or `! codex login`) from a **subscription gap** (nothing to fix; just noting it). The user explicitly wants to hear about a login that failed when they expected it to work.
- Both available → full panel. One available → two-voice panel (Claude + that teammate), still valuable. Neither available → do the review/research yourself and note the panel was unavailable and why.
- Never block, error out, or keep retrying because a teammate is absent.

## The workflow (Claude drives)

### 1. Frame first — form your own view
Before delegating, do your own analysis and write down your provisional answer/plan and the specific things you're unsure about. This is what the panel pressure-tests. Never outsource the thinking; outsource the *checking*.

### 2. Decide the panel (your discretion)
Choose based on the task — you are not required to always use both, or the defaults:
- **How many teammates**: both for high stakes; one if the second adds little.
- **Which models** — maximize independence. For adversarial review, prefer *diverse, strong* models over the fast defaults, e.g.:
  - Cursor → `--model claude-opus-4-8-thinking-high` or `--model gpt-5.5-extra-high`
  - Codex → `-m gpt-5.5 -c model_reasoning_effort=xhigh` (its default) or `-m gpt-5.3-codex` for code-heavy work
- **Web vs codebase vs both** — pick what the question needs. Both CLIs can do live web search and read the repo.
- **Framing** — for review, instruct each teammate to *refute*, not agree (see prompt template).

### 3. Dispatch in parallel (auto mode, read-only)
Run both concurrently in the background so they don't block each other, then collect. Give each the **same self-contained brief** (they have cold context) plus your provisional answer to attack.

```bash
# Cursor teammate — auto mode (--force), read-only (--mode ask), web enabled
cursor-agent -p --force --mode ask --model claude-opus-4-8-thinking-high \
  --workspace "$(pwd)" \
  "$BRIEF" > /tmp/braintrust_cursor.txt 2>&1 &

# Codex teammate — auto mode (approval never), read-only sandbox, web enabled
codex exec --sandbox read-only --skip-git-repo-check \
  -c tools.web_search=true -c approval_policy=never -C "$(pwd)" \
  -m gpt-5.5 -c model_reasoning_effort=xhigh \
  "$BRIEF" > /tmp/braintrust_codex.txt 2>&1 </dev/null &

wait
```

Prefer the Bash tool's `run_in_background` for long runs and read results when they return. Use a generous timeout (up to 600000 ms). See `cursor-research` and `codex-research` for full flag rationale — do not drop the read-only mode flags.

### 4. Reconcile adversarially
Read both outputs. For every claim, ask: does it hold against the actual code / cited sources? Where teammates **agree**, treat as higher-confidence but still verify. Where they **disagree** or contradict you, dig in — that's where the value is. Discard confident-but-wrong claims; verify the rest yourself.

### 5. Synthesize + verify
Deliver one answer in your own voice:
- **Verdict / recommendation** (yours, informed by the panel).
- **Consensus** — what all three independently agreed on.
- **Disagreements** — where they diverged, and your adjudication with reasoning.
- **What changed your mind** — anything a teammate surfaced that you'd missed.
- Verify concrete claims against the code/sources before presenting as fact.

## Prompt template (adversarial framing)

Give each teammate a brief like:

> Context: <all relevant facts, file paths, constraints — they have no prior context>.
> Here is my current plan/answer/diagnosis: <yours>.
> Your job: find the strongest reasons this is WRONG or will FAIL. Check the codebase at the given paths and search the web where relevant. Cite specifics (file:line, URLs). If it's actually sound, say what would make it more robust. Be concrete, not diplomatic.

## Safety

- Both teammates run **auto mode + read-only** — they never hang on approval and never edit files or run write commands. This is enforced by `--mode ask` (Cursor) and `--sandbox read-only` (Codex); keep those flags. Never escalate to write/force-without-mode unless the user explicitly authorizes edits.
- Teammate output is **input, not truth** — Claude verifies before acting or reporting.
- These are outward-facing (web) and quota-spending calls; keep the panel scoped to the stakes.
