#!/usr/bin/env node
// compare.mjs — pixel-diff two PNGs (same dimensions expected; auto-crops to overlap).
//
// Usage: node compare.mjs <a.png> <b.png> [--out diff.png] [--threshold 2]
// Output: DIFF: 1.34% (12345/920000 px)  → exit 0 if <= threshold%, else 1.
// Requires pixelmatch + pngjs (npm i -D pixelmatch pngjs, or run from a repo that has them).

import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';

// Resolve deps from the CURRENT project, not this script's directory.
const requireFromCwd = createRequire(join(process.cwd(), 'noop.js'));
let pixelmatch, PNG;
try {
  const pm = requireFromCwd('pixelmatch');
  pixelmatch = pm.default ?? pm;
  ({ PNG } = requireFromCwd('pngjs'));
} catch {
  console.error('compare.mjs: requires pixelmatch + pngjs in the current project (npm i -D pixelmatch pngjs)');
  process.exit(64);
}

const args = process.argv.slice(2);
const OPTS_WITH_VALUE = new Set(['--out', '--threshold']);
const files = [];
for (let i = 0; i < args.length; i++) {
  if (OPTS_WITH_VALUE.has(args[i])) i++;
  else if (!args[i].startsWith('--')) files.push(args[i]);
}
if (files.length !== 2) {
  console.error('usage: node compare.mjs <a.png> <b.png> [--out diff.png] [--threshold 2]');
  process.exit(64);
}
const opt = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
};
const threshold = parseFloat(opt('threshold', '2'));
const outPath = opt('out', null);

const a = PNG.sync.read(readFileSync(files[0]));
const b = PNG.sync.read(readFileSync(files[1]));
const width = Math.min(a.width, b.width);
const height = Math.min(a.height, b.height);

const crop = (img) => {
  if (img.width === width && img.height === height) return img.data;
  const out = new PNG({ width, height });
  PNG.bitblt(img, out, 0, 0, width, height, 0, 0);
  return out.data;
};

const diff = new PNG({ width, height });
const mismatched = pixelmatch(crop(a), crop(b), diff.data, width, height, { threshold: 0.1 });
if (outPath) writeFileSync(outPath, PNG.sync.write(diff));

const pct = (mismatched / (width * height)) * 100;
console.log(`DIFF: ${pct.toFixed(2)}% (${mismatched}/${width * height} px)${a.width !== b.width || a.height !== b.height ? ' [dimension mismatch — compared overlap only]' : ''}`);
process.exit(pct <= threshold ? 0 : 1);
