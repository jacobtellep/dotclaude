---
name: codex-research
description: Delegate research, analysis, second-opinion, or planning work to the OpenAI Codex CLI (codex exec) as an independent teammate for a genuinely independent take — with live web search and read-only codebase access. Use when asked to "ask Codex", "consult Codex", get an OpenAI second opinion, cross-check a plan/diagnosis, or run a parallel investigation. Runs in auto mode (never hangs) and read-only (never edits). Default model is GPT-5.5 at xhigh reasoning effort; override with a leading --model <id> argument.
argument-hint: "[--model <id>] <research question or task for Codex>"
---

# Codex Research

Use the OpenAI Codex CLI (`codex exec`) as a **research teammate**: a fresh, independent OpenAI-family agent that you delegate scoped investigation, analysis, second opinions, or read-only planning to, then read the result back and apply your own judgment.

The value is independence. A cold-context agent on OpenAI models reasons from scratch and won't inherit your assumptions, so it surfaces blind spots, tie-breaks genuine uncertainty, and adversarially checks plans and diagnoses. It has **live web search** and **read-only** access to the current codebase.

## When to use

- The user says "ask Codex", "consult Codex", "what does Codex think", or wants an OpenAI-family second opinion.
- You want an **independent cross-check** of a plan, design, bug diagnosis, or risky decision.
- You want to **fan out a scoped investigation** (codebase or web) and read the report while you do other work.
- You're **genuinely uncertain** and a second reasoner would break the tie.

Do NOT use it for things you can just do yourself faster — it's slower and spends the user's OpenAI/ChatGPT quota. Reserve it for real research and judgment calls.

## Preflight (once per session)

Confirm the CLI is available and authed before the first call:

```bash
which codex && codex login status
```

If not logged in, tell the user to run `! codex login` themselves (interactive) — do not attempt it headless.

**If Codex is unavailable** (not installed, not logged in, or a subscription/entitlement error) — the user may not currently have an OpenAI/ChatGPT subscription for it. Do not error out or keep retrying. Fall back to `cursor-research` or just do the work yourself — but **always tell the user it was skipped and the specific reason**. Distinguish a **fixable login/auth issue** (say: run `! codex login` to restore it) from a **subscription gap** (nothing to fix; just noting it). Never stay silent — the user wants to know so they can fix a login they expected to work.

## Invocation

Parse the skill arguments:

1. If the arguments begin with `--model <id>`, strip that flag and pass it through as `-m <id>` (dropping the default reasoning-effort override unless the user asks for it). Otherwise **default to `-m gpt-5.5 -c model_reasoning_effort=xhigh`** (GPT-5.5 at extra-high reasoning).
2. The remaining text is the research task. If empty, ask the user what to research.

Then run (auto mode + read-only + web search):

```bash
codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  -m gpt-5.5 -c model_reasoning_effort=xhigh \
  -c tools.web_search=true \
  -c approval_policy=never \
  -C "$(pwd)" \
  "<full task with all context Codex needs>" </dev/null
```

- `-c approval_policy=never` = **auto mode**: never pauses for approval, so it can't hang.
- `--sandbox read-only` = it can read the repo and browse the web but **cannot edit or run write commands**.
- `-c tools.web_search=true` enables **live internet research** (equivalently, `codex --search exec ...`). Just tell it to "search the web for ...".
- `-C "$(pwd)"` sets the working root so it reads the current project. Add `--add-dir <path>` for extra roots.
- `--skip-git-repo-check` lets it run outside a git repo.
- Append `</dev/null` — `codex exec` reads piped stdin as extra input and can stall a headless run without it.
- Use a generous timeout (up to 600000 ms). For long investigations, run in the background and read the result when it returns.
- **Cold context** — it does not see this conversation. Put every relevant fact, file path, constraint, and the exact question into the prompt.

### Useful extras

- `--json` — emit JSONL events for programmatic parsing.
- `--output-schema <file>` — force the final answer to match a JSON Schema (Codex-only; great for structured findings).
- `-o, --output-last-message <file>` — write just the final answer to a file.
- `codex exec resume --last` (or `resume <id>`) — continue the previous session instead of starting cold.
- `codex exec review` — built-in code review over the current repo.

### Model override examples

```bash
# Default (no --model given): GPT-5.5 at xhigh reasoning
codex exec --sandbox read-only --skip-git-repo-check -m gpt-5.5 -c model_reasoning_effort=xhigh \
  -c tools.web_search=true -c approval_policy=never "..." </dev/null

# User passes: --model gpt-5.3-codex  → Codex-family model for code-heavy analysis
# User passes: --model gpt-5.2        → lighter/faster general reasoning
```

Codex has no `--list-models`; models depend on the account. If a passed model is rejected, report the error and suggest dropping `-m` to use the default.

## Safety

- The read-only guarantee comes from `--sandbox read-only`. Keep it. Never use `--dangerously-bypass-approvals-and-sandbox`, `--full-auto`, or `workspace-write`/`danger-full-access` sandboxes unless the user explicitly authorizes edits for a specific task.
- Do not let it trigger destructive or outward-facing actions.
- A benign `rmcp ... AuthorizationRequired` line may appear when an unrelated MCP server can't auth — it does not affect the run; ignore it.

## Using the result

- Treat Codex's output as **input, not truth**. Verify claims against the actual code (and cited sources) before acting; call out where you agree, disagree, and why.
- Relay what matters to the user — the conclusion and any disagreement — not the raw dump.
- For an adversarial check, prompt it to *refute*: "Here is my plan: … Find the strongest reasons this is wrong or will fail."
