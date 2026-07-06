---
name: checks
description: Run the composable verification suite over the current changes — routes to check-code and check-ui based on what changed, and ends with the evidence block. Invoke as /checks, or /checks code|ui for a subset.
disable-model-invocation: true
argument-hint: "[code|ui ...] [base-branch]"
---

# /checks — verification suite dispatcher

Routes the current diff through the check-* family. Sub-skills do the work; this skill only decides which apply and in what order.

## 1. Scope the diff

```bash
git diff --name-only $(git merge-base main HEAD 2>/dev/null || echo HEAD)
git status --short
```

If `$ARGUMENTS` names specific checks (`code`, `ui`), run only those and skip routing.

## 2. Route (run all that match, in this order)

| Condition | Skill to invoke |
|---|---|
| Always (any code change) | **check-code** |
| Changed files match `*.tsx, *.jsx, *.css, *.scss, *.sass`, tailwind config, or component/layout dirs | **check-ui** |

State which routes matched and which were skipped (with the reason) — silent skips read as "covered" when they weren't.

Diff-level bug review (adversarial reading of the whole change) is out of scope for this suite. Run it separately using whatever code-review skill your harness provides.

## 3. Terminal state

After all routed checks complete (including fix → re-run cycles), **invoke the evidence skill** and end with its Evidence block. Do not invoke any other skill after evidence; the Evidence block is the final output of /checks.
