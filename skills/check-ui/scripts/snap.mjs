#!/usr/bin/env node
// snap.mjs — headless UI verification via the chrome-devtools-axi browser CLI.
// Screenshots + console gate + network gate + optional click/assert checks.
//
// Usage:
//   node snap.mjs <url> [--out <dir>] [--viewports 375x812,768x1024,1440x900]
//                 [--click <selector>] [--assert "<js expression evaluating truthy>"]
//                 [--wait <ms|text>] [--full-page]
//
// Output lines (machine-readable):
//   SHOT: <path>                       one per screenshot
//   CONSOLE: <type> <text>             every console error / flagged warning
//   NET: <status> <method> <url>       every 4xx/5xx response
//   ASSERT: PASS|FAIL|ERROR <expression or click(selector)>
//   SNAP: PASS|FAIL console=N network=N asserts=N/N
// Exit 0 iff PASS. Requires chrome-devtools-axi on PATH (npm i -g chrome-devtools-axi).
//
// Real :hover cannot be scripted by CSS selector — verify hover states
// interactively instead: `chrome-devtools-axi snapshot` (find the @uid) →
// `hover @<uid>` → `eval "getComputedStyle(...)"` → `screenshot`.

import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const args = process.argv.slice(2);
const OPTS_WITH_VALUE = new Set(['--out', '--viewports', '--click', '--assert', '--wait']);
let url;
for (let i = 0; i < args.length; i++) {
  if (OPTS_WITH_VALUE.has(args[i])) i++;
  else if (!args[i].startsWith('--')) { url = args[i]; break; }
}
if (!url) {
  console.error('usage: node snap.mjs <url> [--out dir] [--viewports WxH,...] [--click sel] [--assert expr] [--wait ms|text] [--full-page]');
  process.exit(64);
}
const opt = (name) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const optAll = (name) => args.flatMap((a, i) => (a === `--${name}` ? [args[i + 1]] : []));

const outDir = opt('out') ?? '.';
mkdirSync(outDir, { recursive: true });
const viewports = (opt('viewports') ?? '375x812,768x1024,1440x900')
  .split(',')
  .map((v) => v.split('x').map(Number));
const clicks = optAll('click');
const asserts = optAll('assert');
const settle = opt('wait') ?? '1200';
const fullPage = args.includes('--full-page');

// Isolated session so concurrent runs (and the user's own axi session) don't collide.
const ownSession = !process.env.CHROME_DEVTOOLS_AXI_SESSION;
const env = {
  ...process.env,
  CHROME_DEVTOOLS_AXI_SESSION: process.env.CHROME_DEVTOOLS_AXI_SESSION ?? `snap-${process.pid}`,
};
const axi = (cmdArgs) => execFileSync('chrome-devtools-axi', cmdArgs, { encoding: 'utf8', env, timeout: 120_000 });

try {
  axi(['-v']);
} catch {
  console.error('snap.mjs: chrome-devtools-axi not found on PATH. Install: npm i -g chrome-devtools-axi');
  process.exit(64);
}

// eval prints `result: "<value>"` with string values JSON-encoded a second
// time (`result: "\"PASS\""`); thrown errors also land there as "Error: ...",
// so PASS/FAIL/ERROR markers are produced inside the page function.
const evalResult = (fn) => {
  const m = axi(['eval', fn]).match(/^result: ("(?:[^"\\]|\\.)*")/m);
  if (!m) return 'ERROR: unparseable eval output';
  let v = JSON.parse(m[1]);
  try {
    const inner = JSON.parse(v);
    if (typeof inner === 'string') v = inner;
  } catch { /* bare value like true/Error: — keep as-is */ }
  return v;
};
const assertFn = (expr) =>
  `() => { try { return (${expr}) ? 'PASS' : 'FAIL'; } catch (e) { return 'ERROR: ' + e.message; } }`;
const clickFn = (sel) =>
  `() => { try { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) return 'FAIL'; el.scrollIntoView({ block: 'center' }); el.click(); return 'PASS'; } catch (e) { return 'ERROR: ' + e.message; } }`;

const HYDRATION = /hydration|did not match|text content does not match|uselayouteffect.*server/i;
let consoleFails = 0;
let netFails = 0;
let assertFails = 0;
let assertTotal = 0;
const slug = url.replace(/^https?:\/\//, '').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').slice(0, 60);

try {
  for (const [w, h] of viewports) {
    // emulate (CDP device metrics), not resize: window resize clamps to Chrome's 500px minimum width.
    axi(['emulate', '--viewport', `${w}x${h}`]);
    try {
      axi(['open', url]);
    } catch (e) {
      consoleFails++;
      console.log(`CONSOLE: pageerror navigation failed — ${String(e.message ?? e).split('\n')[0]}`);
      continue;
    }
    axi(['wait', settle]);

    const shot = join(outDir, `${slug}-${w}.png`);
    axi(['screenshot', shot, ...(fullPage ? ['--full-page'] : [])]);
    console.log(`SHOT: ${shot}`);

    for (const sel of clicks) {
      assertTotal++;
      const r = evalResult(clickFn(sel));
      if (r !== 'PASS') { assertFails++; console.log(`ASSERT: ${r.startsWith('ERROR') ? 'ERROR' : 'FAIL'} click(${sel})${r.startsWith('ERROR') ? ` — ${r.slice(7)}` : ''}`); }
    }
    for (const expr of asserts) {
      assertTotal++;
      const r = evalResult(assertFn(expr));
      if (r === 'PASS') console.log(`ASSERT: PASS ${expr}`);
      else { assertFails++; console.log(`ASSERT: ${r.startsWith('ERROR') ? `ERROR ${expr} — ${r.slice(7)}` : `FAIL ${expr}`}`); }
    }

    // Gates run last so errors triggered by clicks are caught too.
    // The console resets on each navigation, so counts are per-viewport.
    for (const m of axi(['console', '--type', 'all', '--limit', '500']).matchAll(/^msgid=\d+ \[(\w+)\] (.*)$/gm)) {
      const [, type, text] = m;
      if (type === 'error' || (type === 'warn' && HYDRATION.test(text))) {
        consoleFails++;
        console.log(`CONSOLE: ${type} ${text}`);
      }
    }
    for (const m of axi(['network', '--limit', '500']).matchAll(/^reqid=\d+ (\S+) (.*) \[(\d{3})\]$/gm)) {
      const status = Number(m[3]);
      if (status >= 400) { netFails++; console.log(`NET: ${status} ${m[1]} ${m[2]}`); }
    }
  }
} finally {
  if (ownSession) { try { axi(['stop']); } catch { /* best effort */ } }
}

const pass = consoleFails === 0 && netFails === 0 && assertFails === 0;
console.log(`SNAP: ${pass ? 'PASS' : 'FAIL'} console=${consoleFails} network=${netFails} asserts=${assertTotal - assertFails}/${assertTotal}`);
process.exit(pass ? 0 : 1);
