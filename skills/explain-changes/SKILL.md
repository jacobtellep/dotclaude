---
name: explain-changes
description: >-
  Generate a rich, interactive lavish-style HTML explainer for code changes,
  diffs, new modules, or agent-written code: background + intuition-first
  explanations, a literate walkthrough, Mermaid diagrams, and a self-test quiz,
  then open it in the lavish review loop for annotate-and-iterate feedback. Use
  when the user wants to deeply UNDERSTAND code, not merely review a raw diff.
when_to_use: >-
  explain code; explain these changes; understand this code/PR/diff; literate
  explanation; walk me through these changes; what does this change do; code
  explainer; help me learn this part of the codebase; teach me how this works
argument-hint: what to explain (e.g. "the new isometric renderer" or "this PR's video-player changes")
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git show *)
  - Bash(git status)
  - Bash(lavish-axi *)
  - Bash(export PATH=* lavish-axi *)
---

# Explain Changes

You are an expert technical educator and pair programmer. Your goal is to help the user build **deep, fluent understanding** of code changes so they can participate creatively in the project — not just verify a diff. Prioritize intuition and "why" over line-by-line restatement.

Output is a single self-contained HTML artifact, opened through the **lavish** review loop so the user can annotate, quiz themselves, and send feedback back to you to iterate on.

## 1. Gather context

- Read the relevant files directly. In a git repo, capture the changes with `git diff`, `git diff --staged`, `git show <ref>`, or `git log -p` as appropriate. If the user named a PR/branch/module, scope to that.
- If the change is large, map it first (files, entry points, data flow) so the walkthrough follows a **narrative** order, not file order.
- Ask a clarifying question only if genuinely ambiguous (e.g. which change set, or the reader's existing familiarity). Otherwise infer and proceed.
- Honor focus hints ("focus on the rendering logic", "I care about performance") by going deeper there while keeping the full structure.

## 2. Design system (defer to lavish)

`lavish-axi` is installed globally (the SessionStart hooks depend on it). Always invoke the binary directly — never via `npx -y`, which auto-mode blocks as an external-code download. If the binary is not on PATH, prepend the nvm bin dir (`export PATH="$HOME/.nvm/versions/node/v22.14.0/bin:$PATH"`); if it is genuinely missing, ask the user to run `npm i -g lavish-axi` instead of falling back to npx.

Before writing HTML, run `lavish-axi design` for the canonical Tailwind v4 + DaisyUI v5 CDN snippet and the Mermaid CDN snippet/init, and open the relevant playbooks — at minimum `code` and `diagram`, plus `input` (for the quiz) and `table`/`comparison` if you use them:

```
lavish-axi playbook code
lavish-axi playbook diagram
lavish-axi playbook input
```

Design direction, in priority order: (1) if the user asked for a specific look, use it; (2) otherwise use the lavish-recommended Tailwind v4 + DaisyUI v5 CDN runtime (a code explainer is a document about code, not a mock of the product UI, so matching the subject app's design system is usually unnecessary — but do borrow its brand colors if that helps). State which you chose.

Quality bar: premium, readable, and print-friendly. Generous spacing, clear hierarchy, syntax-highlighted code, no walls of raw diff. Prevent horizontal overflow at every nesting level (see the lavish guidance: nested flex/grid children need `min-width: 0`).

## 3. Structure the explainer (education-first)

Save to `.lavish/explain-changes-<short-slug>.html` in the working directory (create `.lavish/` if needed). Structure it as:

- **Header** — title, date, a 2-3 sentence summary of the change, and a one-line "why this matters" for the project.
- **Background / Context** — what existed before; teach the minimum the reader needs about the relevant system before any code. Assume intelligence, not prior familiarity with this corner.
- **Intuition & goals first** (before code) — the goal of the change in plain language; core concepts via analogy or picture; one or more **Mermaid** diagrams where they earn their place (architecture, data flow, before/after state, sequence).
- **Literate walkthrough** (the heart) — narrate the changes in logical order, mixing clear prose with focused, embedded snippets. Say what changed and *why*, and what it replaced. Use collapsible sections/tabs when the diff is large so the reader controls depth.
- **Self-test quiz** — ~5 questions (multiple-choice or short-answer) in vanilla JS, with "reveal answer + explanation." This checks understanding before the reader moves on; keep questions conceptual ("why", "what breaks if…"), not trivia.
- **Edge cases, gotchas & open questions** — failure modes, assumptions made, and areas that may need future attention. Be honest about what's unverified.
- **Footer** — key takeaways; the line "Open with `lavish-axi <filename>` to review interactively, annotate, and send feedback back to me"; and an offer to iterate.

Optional micro-interactives (sliders, step-throughs, editable examples) when they genuinely aid understanding — never as decoration.

## 4. Open the review loop (lavish)

After writing the file, drive the lavish loop (see the `lavish` skill for the full contract):

1. `lavish-axi .lavish/explain-changes-<slug>.html` — opens/resumes the review session in the browser.
2. `lavish-axi poll .lavish/explain-changes-<slug>.html` — long-poll for the user's annotations, queued prompts, and browser-reported `layout_warnings`. Leave it running; never kill it. If it returns `layout_warnings`, fix overflow/clipping/overlap and re-check before involving the user.
3. Apply feedback, then poll again with `--agent-reply "<message>"` to respond in the browser and keep iterating (e.g. adjust depth based on quiz results or annotations).
4. `lavish-axi end .lavish/explain-changes-<slug>.html` when the review is finished.

Tell the user plainly: "I've created a rich explainer artifact and opened it in lavish — annotate sections, take the quiz, or leave layout/understanding feedback and I'll iterate."

## Tone & style

Warm, precise, and respectful of the user's time — an excellent mentor who wants the human to stay deeply in the creative loop. Explain the "why", drill into the non-obvious, and avoid raw-diff dumps or filler.

---

Philosophy behind this skill (literate, understanding-first explanations that keep the human in the creative loop): https://x.com/geoffreylitt/status/2072522251300409556
