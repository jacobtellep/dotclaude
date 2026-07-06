---
argument-hint: [instructions]
description: Interview user in-depth to create a detailed spec
allowed-tools: AskUserQuestion, Write, Read, Glob, Grep, Bash
---

Follow the user instructions and interview me in detail using the AskUserQuestionTool about literally anything: technical implementation, UI & UX, concerns, tradeoffs, etc. but make sure the questions are not obvious. be very in-depth and continue interviewing me continually until it's complete. then, write the spec to a file (via the `spec` skill's format when the work is agent-executable). <instructions>$ARGUMENTS</instructions>

## Educate-to-decide (when I can't answer)

When I signal uncertainty ("I don't know", "what would you do?", "no idea", visible hesitation), do NOT skip the question or silently pick for me. Escalate this ladder, cheapest first:

1. **Codebase first.** If the answer is discoverable (existing patterns, configs, prior art), explore and answer it yourself — most "I don't know"s are really "the code knows". Tell me what you found and move on.
2. **Teach to the decision, not the domain.** Present 2-4 concrete options via AskUserQuestion **with previews** (side-by-side mockups, code snippets, config diffs) — recommendation first and marked. Each option states its tradeoff and consequence. **Every consequence claim ("picking B breaks X") must cite evidence (file:line, doc link) or be explicitly labeled "assumption"** — I'm mid-learning and can't audit fabricated tradeoffs. No more education than this one decision needs.
3. **Genuinely conceptual gap only** (I don't understand the domain the decision lives in): generate one small interactive explainer (lavish / explain-changes pattern — a diagram and a comparison, not a wall of markdown), scoped to exactly the concept blocking this answer. Then re-ask via step 2.

Mark every answer that came through this ladder as **(decided via education)** in the interview output/spec, so those decisions get revisited once I know more.
