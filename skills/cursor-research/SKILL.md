---
name: cursor-research
description: Delegate research, analysis, second-opinion, or planning work to the Cursor CLI (cursor-agent) as an independent teammate — optionally a different model family (GPT-5.x, Codex, Opus) for a genuinely independent take. Use when asked to "ask Cursor", "consult Cursor", get a second opinion, cross-check a plan/diagnosis, or run a parallel investigation. Default model is Composer 2.5 (Cursor's own model); override with a leading --model <id> argument.
argument-hint: "[--model <id>] <research question or task for Cursor>"
---

# Cursor Research

Use the locally-installed Cursor CLI (`cursor-agent`) as a **research teammate**: a fresh, independent agent — often a *different model family* — that you delegate scoped investigation, analysis, second opinions, or read-only planning to, then read the result back and apply your own judgment.

The value is independence. A cold-context agent on GPT-5.5 / Codex reasons from scratch and won't inherit your assumptions, so it surfaces blind spots, tie-breaks genuine uncertainty, and adversarially checks plans and diagnoses.

## When to use

- The user says "ask Cursor", "consult Cursor", "what does Cursor think", or "get a second opinion".
- You want an **independent cross-check** of a plan, design, bug diagnosis, or risky decision before committing.
- You want to **fan out a scoped investigation** (e.g. "map how auth flows through this repo") and read the report while you do other work.
- You're **genuinely uncertain** and a second reasoner would break the tie.

Do NOT use it for things you can just do yourself faster — it's slower and spends the user's Cursor quota. Reserve it for real research and judgment calls.

## Preflight (once per session)

Confirm the CLI is available and authed before the first call:

```bash
which cursor-agent && cursor-agent status
```

If not logged in, tell the user to run `! cursor-agent login` themselves (interactive) — do not attempt it headless.

**If Cursor is unavailable** (not installed, not logged in, or a subscription/entitlement error) — the user may not currently have a Cursor subscription. Do not error out or keep retrying. Fall back to `codex-research` or just do the work yourself — but **always tell the user it was skipped and the specific reason**. Distinguish a **fixable login/auth issue** (say: run `! cursor-agent login` to restore it) from a **subscription gap** (nothing to fix; just noting it). Never stay silent — the user wants to know so they can fix a login they expected to work.

## Invocation

Parse the skill arguments:

1. If the arguments begin with `--model <id>`, strip that flag and use `<id>` as the model. Otherwise **default to `composer-2.5`** (Cursor's own fast model).
2. The remaining text is the research task. If empty, ask the user what to research.

Then run (auto mode + read-only — never hangs on approval, and can't edit files):

```bash
cursor-agent -p --force --mode ask --model composer-2.5 \
  --workspace "$(pwd)" \
  "<full task with all context Cursor needs>"
```

- `--force` = **auto mode**: auto-approves tool calls so the run never hangs waiting for a prompt. It also unblocks web search/fetch (headless runs block those without it).
- `--mode ask` is what keeps it **read-only** — it can read files and browse the web but cannot edit. Never drop the mode flag while `--force` is set. For design/architecture tasks use `--plan` (also read-only) instead of `ask`.
- Use a generous timeout (up to 600000 ms). For long investigations, run in the background and read the result when it returns.
- The teammate has **cold context** — it does not see this conversation. Put every relevant fact, file path, constraint, and the exact question into the prompt. Vague prompts get vague answers.
- Prefer `--output-format text` (default) for reading. Use `--output-format json` only when you need to parse it programmatically.
- Web research works out of the box in this configuration — just tell it to "search the web for ...".

### Modes (both read-only — pick by task)

- `--mode ask` — Q&A, explanations, second opinions, focused research. **Default.**
- `--plan` (or `--mode plan`) — read-only analysis that proposes a plan/design. Use for architecture and "how should we approach X" tasks.

### Repo-aware research

Add `--workspace "$(pwd)"` so it can read the current repo, and `--add-dir <path>` for extra roots. This lets it ground answers in real code instead of guessing.

### Model override examples

```bash
# Default (no --model given): Composer 2.5
cursor-agent -p --force --mode ask --model composer-2.5 "..."

# User passes: --model gpt-5.5-extra-high            → GPT-5.5 for deep reasoning
# User passes: --model gpt-5.3-codex-high            → Codex for code-heavy analysis
# User passes: --model claude-opus-4-8-thinking-high → Opus teammate (independent cross-check)
```

List valid ids with `cursor-agent --list-models` if a passed model isn't recognized; suggest the closest match rather than failing silently.

## Safety

- The read-only guarantee comes from the **mode** (`--mode ask` / `--plan`), not from withholding `--force`. Auto mode (`--force`) only auto-approves the tool calls the mode already allows, so it never edits files.
- **Never run `--force` without a read-only mode flag.** `--force` alone (or with a write-capable mode) lets it edit and run anything — only do that if the user explicitly authorizes edits for a specific task.
- Do not let it trigger destructive or outward-facing actions.

## Using the result

- Treat Cursor's output as **input, not truth**. Verify claims against the actual code before acting; call out where you agree, disagree, and why.
- Relay what matters to the user — the conclusion and any disagreement — not the raw dump.
- For an adversarial check, prompt it to *refute*: "Here is my plan: … Find the strongest reasons this is wrong or will fail."
- To continue a line of inquiry with the same teammate, reuse `--continue` (or `--resume <chatId>`) instead of starting cold.
