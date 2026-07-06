---
name: evidence
description: Produce the mandatory Evidence block from fresh verification before any completion claim. Use before committing or opening a PR, before saying "done"/"fixed"/"should work", or when asked "did you test this".
---

# evidence — done means proven

The Iron Law: **no completion claims without fresh verification evidence.** If you haven't run the verification in *this* part of the conversation, you cannot claim it passes.

## Claims require evidence

| Claim | Required evidence | NOT acceptable |
|---|---|---|
| "Tests/checks pass" | A `VERIFY:` line from check-code run this turn | A run from earlier, "should pass" |
| "The UI works" | A `VERIFY-UI:` line + screenshots from check-ui | Reading the code, "looks right" |
| "Subagent finished X" | The VCS diff showing X's changes | The subagent's own report (claims, not facts) |

## Rationalizations (rejected in advance)

- "Linter passed" — linter ≠ compiler ≠ tests ≠ working UI.
- "It's a tiny change" — tiny changes broke shared buttons across sites before.
- "I'm confident" — confidence is not evidence.
- "Different words, so the rule doesn't apply" — spirit over letter.

## Steps

1. Collect from this conversation: every verification command actually run + exit code; the latest `VERIFY:` and `VERIFY-UI:` lines; screenshot paths.
2. If the change is code and nothing was verified this turn: run **check-code** now (and **check-ui** if anything user-visible changed). Then return here.
3. End your completion message with exactly this block:

```
## Evidence
Commands:     <each command run, with exit code>
Verify:       <VERIFY: line, verbatim>
UI:           <VERIFY-UI: line + screenshot paths, or "n/a — no visual change">
NOT verified: <mandatory, never empty — deploy environment, real CMS content,
               other browsers, caching behavior… there is always something>
```

## Rules

- Never write "should work", "probably fine", or claim success for anything in the NOT-verified line.
- The NOT-verified line is honest scope, not failure — it tells the user exactly what still needs human or deploy-time eyes.
- No Evidence block → the task is not done.
