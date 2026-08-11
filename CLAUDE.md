# Claude Code adapter

## Browsers

Automate with `playwright-cli` (shell): driving pages, forms, assertions.
Diagnose with the Chrome DevTools MCP: performance traces, Lighthouse, heap snapshots.
Use my running Chrome via `claude-in-chrome`: signed-in sessions, open tabs, my real profile.

Playwright ships CLI-first, Chrome DevTools MCP-first — each is that vendor's own recommendation.

## Pull requests

Before writing any PR body — `gh pr create`, `gh pr edit --body`, or a PR you decided to open yourself — invoke the `pr-description` skill and follow it.

## Personal reference files

Read `~/OPINIONS.md` when a technical or product decision would benefit from my established views.
Read `~/VOICE.md` before drafting in my voice.

## Coding standards file

Most of my repos keep a personal `CODING_STANDARDS.md` at the repo root.
Read and follow it before writing or reviewing code.
It is deliberately untracked and globally gitignored, so search tools that respect gitignore will not surface it; check for it by path with a direct read.
