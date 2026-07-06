---
name: check-ui
description: Verify user-visible changes in a real browser with hard assertions (console, hydration, computed styles, geometry) and screenshots before claiming visual work is done. Use after changing CSS, markup, layout, or interactive UI states (hover, modals, drawers, z-index, responsive breakpoints).
argument-hint: "[url] [--compare <prod-url>] [--routes /a,/b]"
paths:
  - "**/*.{tsx,jsx,vue,svelte,astro}"
  - "**/*.{css,scss,sass,less}"
---

# check-ui — browser verification loop

Part of the `/checks` family. The pass/fail signal is **machine-checkable assertions** — console state, computed styles, geometry, network status. Screenshots are supporting evidence for the human, never the verdict.

## 1. Pick the target URL (in priority order)

1. URL given in `$ARGUMENTS`.
2. A deploy-preview URL already in this conversation (`*.netlify.app`, `*.vercel.app`).
3. An already-running dev server — probe `localhost:3000` and any port in the project's `dev` script.
4. Start the dev server yourself in the background (`run_in_background`), wait for the ready line, parse the **actual** port from output (Next auto-increments when ports collide across worktrees). Never block the foreground on it.

## 2. Pick the browser tool (in priority order)

1. **chrome-devtools-axi CLI** (plain Bash, so it works in subagents too; launches its own headless Chrome): `open <url>`, `emulate --viewport WxH`, `snapshot`, `eval <js>`, `console`, `network`, `screenshot <path>`, `hover @<uid>`, `run` (scripted `page` API via stdin). Use `emulate`, not `resize`, for widths under 500 — window resize clamps to Chrome's 500px minimum. Set `CHROME_DEVTOOLS_AXI_SESSION=<name>` when running concurrent checks so sessions don't collide.
2. **Claude in Chrome MCP** (`mcp__claude-in-chrome__*`): `navigate`, `read_page`, `computer`, `javascript_tool`, `read_console_messages`, `read_network_requests` — drives the user's real Chrome session, so prefer it for authenticated pages.
3. **Chrome DevTools MCP** (`mcp__plugin_chrome-devtools-mcp_chrome-devtools__*`): `navigate_page`, `take_snapshot`, `evaluate_script`, `list_console_messages`, `list_network_requests`, `take_screenshot`, `resize_page`, `hover`.
4. **Batch fallback** (subagents/no MCP): `node ~/.claude/skills/check-ui/scripts/snap.mjs <url> --out <dir> ...` — screenshots + console/network gates + JS asserts across viewports, built on chrome-devtools-axi (no project deps). Real `:hover` can't be scripted by selector; verify it interactively via `snapshot` → `hover @<uid>` → re-`eval` the computed style.

Note: headless axi/DevTools Chrome runs a fresh profile with no cookies — for authenticated pages use Claude in Chrome (option 2). Chrome 136+ blocks remote debugging on the default profile, so attaching axi to your logged-in Chrome needs a dedicated debugging profile.

## 3. Decide what to verify

Map the diff to routes: `git diff --name-only` → grep which pages import the changed components. Verify each affected route. Ask only if genuinely ambiguous.

## 4. The loop — per route, assert don't eyeball

Save all screenshots to `~/.cache/agent-evidence/<project>/<timestamp>/`.

For each route, at the viewports the change can actually affect — default **375, 768, 1440**. You may verify fewer **only** when the change is provably viewport-independent (a single asset swap, a color token, a copy edit); when you do, name which viewports you ran and why you dropped the rest in the verdict line. The console, network, hydration, and geometry gates below are **never** optional — they run at every viewport you do verify.

1. Navigate, wait for content, `take_snapshot` (a11y tree) — assert the changed elements are present.
2. **Console gate** (hard fail): read console messages. FAIL on any error. FAIL on warnings matching `Hydration`, `did not match`, `Text content does not match`, `useLayoutEffect.*server`. Hydration warnings are bugs, not noise.
3. **Network gate**: no new 4xx/5xx on the route's requests.
4. **Interaction assertions** via `evaluate_script` / `chrome-devtools-axi eval` — for whichever apply to the change:
   - **Hover**: capture `getComputedStyle(el)` color/background at rest, hover the element, re-read — assert it actually changed (and isn't e.g. white-on-white). Screenshot mid-hover.
   - **Drawer/modal**: open it; assert visibility and, at 375px, `el.getBoundingClientRect().height` ≈ `window.innerHeight` (the dvh class of bug). Close it; assert it's gone from the snapshot.
   - **Stacking**: assert the element's effective z-index puts it above the overlays it must beat (compare computed z-index along both stacking contexts, or elementFromPoint at the overlap).
   - **Shadow/overflow clipping**: assert no ancestor between the element and its shadow's extent has `overflow: hidden` that intersects the shadow box; screenshot with surrounding context.
5. Screenshot each verified state.

## 5. Optional prod compare (`--compare <prod-url>`)

Same route + viewport on prod. Side-by-side screenshots, then:

```bash
node ~/.claude/skills/check-ui/scripts/compare.mjs local.png prod.png
```

Reports `DIFF: n%`. Judge against ~2%: the intentional change should diff; **anything else that moved is a regression**.

## 6. Verdict

Emit one line (consumed by the evidence skill). **Every claimed check must name the mechanism that proved it** — a lazy eyeball and a real assertion must never produce the same line. Use `assertion=evidence` form, not bare state names:

| Don't write | Write |
|---|---|
| `states=hover` | `hover=getComputedStyle Δconfirmed(#333→#fff)` |
| `states=drawer` | `drawer=getBoundingClientRect h=812≈innerHeight` |
| `states=stacking` | `stack=elementFromPoint hit @overlap` |
| `console=CLEAN` | `console=CLEAN(0 err, 3 baseline warns)` |

List the actual viewports, not a count, and if fewer than three, say why inline:

```
VERIFY-UI: routes=2 viewports=375,768,1440 hover=getComputedStyle Δconfirmed drawer=rect≈innerHeight console=CLEAN network=CLEAN compare=1.3% → PASS
VERIFY-UI: routes=1 viewports=1440(viewport-independent asset swap) img-src=verified console=CLEAN → PASS
```

A field you cannot back with a mechanism does not belong on the line — drop it, or go run the assertion. If the verdict reads like something you could have written without opening a browser, you haven't verified it.

On failure: **fix it and re-run the loop yourself — the user is not the test oracle.** Max 3 fix cycles, then report honestly with screenshots of the failing state and what you tried.
