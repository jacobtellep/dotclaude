# Spec: /work — reconciler-style agentic workflow

spec-version: 2026-07-02.3
owner: Jake (desired state is Jake-editable only; agents may only append to Status)
state: built — awaiting Jake's acceptance of the built work (spec accepted 2026-07-02)

## Intent

Jake's agent results improved dramatically once verification became real; this upgrade makes the whole lifecycle level-triggered, not just the checks.
One front door (/work) sizes every task, extracts intent (teaching Jake when he can't answer), writes a durable reconciler-style spec when warranted, and defines acceptance so that "done" always means "Jake verified it" — while any fresh session can resume any task from the spec plus fresh observation alone.
Goals, per interview: trust agent output with less anxiety, keep Jake learning and in the creative loop, and scale to more parallel agents. Not a goal: teammate-facing polish.

## Decisions of record (interview, 2026-07-02)

- Ceremony gate: the agent sizes the task (none / lite / full spec) and states its call in one line; Jake can override. Trivial tasks get no file.
- Spec home: in-repo `specs/<slug>.md`, committed with the work; archived to `specs/done/` on acceptance.
- Jake's acceptance pass: guided smoke test + risk-ranked reading (5-15 min), generated from the ensure-list.
- Education default: AskUserQuestion options with previews + marked recommendation; codebase exploration always tried first; lavish explainers only for genuinely conceptual gaps.
- Status: milestone-only appends, version-stamped, evidence pointers, written last. "Unknown" check verdicts flag in the acceptance pack, never block handoff.
- Resume: explicit `/work <slug>` plus description-trigger on "continue/resume/pick up"; author mode ends by printing the exact resume command.
- Entry shape: thin gate that only assesses and routes; stages remain independent skills (controller stack).
- Consolidation: now, data-driven (30-day usage counts below).
- Pilot: next real task, any project.

## Desired state

1. **Ensure `/work` exists** (`~/.claude/skills/work/SKILL.md`): a thin gate that (a) sizes the incoming task and states its sizing call in one line, (b) routes to `interview` when intent is unclear, (c) invokes spec authoring for lite/full tasks, (d) hands execution to the existing stack (`goal`, `checks`, `evidence`), and (e) finishes by delivering the acceptance pack. It owns no stage logic itself and stays under 150 lines. **Sizing is a checklist, not judgment**: "no spec" is allowed only when ALL hold — single file touched, no shared/exported surface, one observable check, reversible in one commit; anything borderline gets a lite spec. No-spec tasks still end with the evidence block, so the floor never drops below today's bar.
2. **Ensure a `spec` skill exists** (`~/.claude/skills/spec/SKILL.md` + template) with author and reconcile modes, producing specs with exactly these sections: Intent; Desired State (numbered "ensure X" statements, every one observable; agents never edit); Acceptance Checks (per criterion: an executable command or concrete browser procedure, pass/fail/unknown, an effective-state vs written-state flag, and a cheap-per-loop vs expensive-pre-acceptance tier); Non-goals & Ownership (do-not-touch surfaces, file-level owners); spec-version stamp; Status (append-only, milestone-only, version-stamped, written last); Acceptance Protocol for Jake (what to run/click, 1-3 risk-ranked code hunks to read, what good looks like); Teardown. **An "unknown" verdict must carry the reason it was unverifiable** (e.g. "CI only runs on the PR itself") — "didn't run it" is not a valid unknown — and a full-spec handoff requires the majority of criteria verified against effective (running) state. **The skill ships `scripts/validate-spec.sh`**: checks the eight sections exist, every Desired State line starts with "Ensure", and every criterion has a corresponding check row; author and reconcile modes both run it, so format drift is machine-caught, not aspirational.
3. **Ensure reconcile mode is level-triggered**: a fresh session gathers everything first (spec, checks, git state), distrusts any Status entry older than the current spec-version, computes the gap against the ensure-list, then acts or reports converged. Before any publishing write (commit/push/PR): re-observe (rebase + re-run cheap checks); if the spec changed mid-task, stop and re-plan rather than continue on stale intent.
4. **Ensure `interview` gains the educate-to-decide branch**: on an "I don't know" signal, escalate (1) answer from the codebase, (2) AskUserQuestion with 2-4 previewed options + marked recommendation and consequences, (3) small lavish explainer for conceptual gaps only. **Every consequence claim in an option ("picking B breaks X") must cite evidence (file:line, doc link) or be explicitly labeled "assumption"** — Jake is mid-learning at that moment and cannot audit fabricated tradeoffs. Decisions made via education are flagged in the interview output for later revisit. Frontmatter tools expand to include Read/Glob/Grep/Bash.
5. **Ensure the non-negotiable reconciler rules are stated in the spec template itself**: agents never edit Desired State; acceptance evidence must observe effective state (rendered/running), not file contents alone; status is facts-after-action, never intentions.
6. **Ensure consolidation lands with this change** (30-day usage data): retire `grill-me` and `grill-with-docs` (0 uses; their adversarial decision-tree behavior folds into interview's education branch), and retire `to-issues`, `triage`, `prototype`, `zoom-out`, `handoff`, `migrate`, `logs`, `caveman` (0 uses each). `tdd` (0 uses) demotes to a reference file under the spec skill's execution guidance rather than a listed skill. `to-prd` stays (external-facing artifacts). `educate`, `teach`, `done` stay pending Jake's call (0-3 uses but distinct purposes). Retired skill dirs move to `~/.claude/skills-retired/` (reversible), not deleted.
7. **Ensure resume works cold**: `/work <slug>` reconciles an existing spec; the skill description triggers on continue/resume phrasing; author mode's last line prints the resume command. `/work` with no arguments lists unconverged specs in the repo.
8. **Ensure the spec skill helps derive the bar, not just record it** (added at Jake's direction, 2026-07-02.3): author mode classifies every criterion as readiness / regression guard / guardrail; guardrail metrics require an explicit threshold + baseline (never bare "faster X") and can never gate handoff alone — at least one readiness criterion (user-observable proof the feature works) is mandatory or the spec is not authorable. When Jake can't state the bar, the skill proposes parity / baseline-relative / story-based candidates via previewed options and lets him pick.
9. **Ensure an independent party grades the homework at full tier**: before a full-spec task reaches "awaiting Jake's acceptance", a fresh-context subagent — given ONLY Intent + Desired State + the diff, never the implementer's reasoning or status log — attempts to refute each criterion ("show this isn't really met"). Surviving criteria are marked independently-verified in the acceptance pack; refuted ones go back to reconcile. This is harness-native (a plain subagent) and must NOT depend on external CLIs; when braintrust/Cursor/Codex happen to be available they may be used as an upgrade, but their absence never degrades the baseline. Lite specs skip this; the evidence block covers them.

## Acceptance checks

| # | Check | How | Tier |
|---|---|---|---|
| 1 | Gate sizes correctly | Fresh session: `/work fix the typo in README` → gate says "no spec" and just does it; `/work add rate limiting to the API` → gate proposes a full spec | cheap |
| 2 | Education branch fires | Fresh session interview where Jake answers "I don't know" → agent explores codebase first, then presents previewed options with a recommendation, never a markdown wall | cheap |
| 3 | Spec format holds | Author mode output contains all eight sections; every Desired State line is observable; acceptance protocol references only real commands | cheap |
| 4 | Reconcile is stateless | Kill a session mid-task; fresh session `/work <slug>` reconstructs state from spec + fresh observation and continues correctly | expensive |
| 5 | Stale-status distrust | Edit the spec's Desired State, bump version; next reconcile explicitly re-verifies previously-passing criteria | expensive |
| 6 | Consolidation reversible | Retired skills absent from listing; restoring one from skills-retired/ takes one `mv` | cheap |
| 7 | Gate resists under-sizing | Borderline task (two files, one touching a shared component) → gate must choose lite spec, not no-spec; checklist reasoning stated | cheap |
| 8 | Validator catches drift | Hand it a spec missing a section / a non-"Ensure" line → validate-spec.sh exits non-zero naming the violation | cheap |
| 9 | Refutation pass is real | Full-tier dry run: implementer leaves one criterion subtly unmet → fresh-context refuter catches it from Intent + Desired State + diff alone | expensive |

## Non-goals & ownership

- Non-goals v1: child-spec / multi-agent decomposition machinery; teammate-facing documentation; deleting `educate`/`teach`/`to-prd`; any change to `goal`, `commit`, `checks`, `evidence`, `wt`, `push`.
- Ownership: `~/.claude/skills/work/` and `~/.claude/skills/spec/` are new (this work's); `interview/SKILL.md` is modified by this work only; everything else untouched.

## Acceptance protocol (Jake)

1. Read the two new SKILL.md files end to end (target: <150 lines each) and the modified interview skill (~30 lines).
2. Run checks 1-3 above yourself in a fresh session (~10 min total).
3. Approve or amend the retire list in ensure-6 — this is the one decision made on data you haven't personally confirmed.
4. Risk-ranked reading: the spec template file (it encodes every rule that governs future agents) — read it hardest.

## Status

- 2026-07-03 (spec-version 2026-07-02.3): FORWARD PILOT RAN - three new migration tasks (i18n #395, Marketo/Calc #396, Algolia #394) executed spec-first through /work. Worked: spec-before-code held in all three (validator OK pre-implementation); bar derivation produced behavioral readiness criteria (byte-identical .de sitemap, field-by-field payload parity, live-index shape parity); unknown-with-reason + jake-steps produced 8 concrete boundary handoffs, zero boundary crossings; refutation pass was non-trivial (marketo 10/12 verified, 2 forced reconciliation; algolia 8/8); statelessness validated in production - two crews died mid-task and resumed losslessly from spec + fresh observation; needs-decision loop ran end-to-end once (rosetta creds) with options + recommendation. Friction/gaps: Ownership section covers files but not runtime resources (cross-crew dev-server kill on port 3002); specs/evidence/ dir with committed captures was emergent, not specified - codify it; "reconciled" refutation verdicts lack required disposition notes; gate sizing (none/lite) still unexercised - all pilots were pre-sized full; interview educate branch still untested with Jake directly (meta checks 1, 2, 7 remain his).
- 2026-07-02 (spec-version 2026-07-02.3): PILOT RAN — three real completed migration tasks retro-spec'd through /work→spec by their own resumed agents (auto permission mode). Results: specs/test-infra-w7.md (5 criteria), specs/visual-fixes-e9.md (7), specs/brand-sites-q4.md (7 + panel verdicts recorded as refutation) all validator-OK and pushed to their draft PRs (#391/#392/#393, all still draft); two crews independently re-ran their suites before push (200+88, 216+91 green) — reconcile-mode's re-observe instinct held without being prompted. Friction observed: none in the skills themselves; all friction was session plumbing (resume without autonomy flag, queued-message pile-up) owned by firstmate, not /work. Checks 3+8 previously verified; this pilot exercises authoring at scale; checks 1, 2, 7 (fresh-session gate/education tests) remain Jake's; 4, 5, 9 still open for a live forward task.
- 2026-07-02 (spec-version 2026-07-02.3): Jake directed the bar-derivation addition (new ensure-8, prior 8→9). Implemented: spec author mode step 1b (criterion classes readiness/guard/guardrail, threshold+baseline rule for metrics, readiness-criterion-mandatory rule, parity/baseline-relative/story-based candidate bars via previewed options); template check table gained a `class` column. Evidence: validate-spec.sh → OK (9 criteria, 9 checks, exit 0).

- 2026-07-02 (spec-version 2026-07-02.1): spec authored from interview; no build started. Awaiting Jake's acceptance.
- 2026-07-02 (spec-version 2026-07-02.2): Jake accepted the spec; build executed. skills/work/SKILL.md (thin gate, sizing checklist) and skills/spec/ (SKILL.md + references/template.md + scripts/validate-spec.sh + references/tdd/ demoted guide) created; interview educate-to-decide branch added with expanded tools; 10 zero-use skills + tdd moved to ~/.claude/skills-retired/ (originals intact, one mv restores). Evidence: validate-spec.sh passes this spec (8 criteria, 9 checks, exit 0) and names all violations on a deliberately broken spec (exit 1) — checks 3 and 8 verified. Checks 1, 2, 7 await Jake's fresh-session pass per the Acceptance Protocol; checks 4, 5, 9 exercise during the pilot (next real task through /work).
- 2026-07-02 (spec-version 2026-07-02.2): amended per Jake's direction after failure-mode review — objective sizing checklist + no-spec evidence floor (ensure-1), unknown-requires-reason + majority-effective-state handoff + validate-spec.sh (ensure-2), evidence-cited education claims (ensure-4), harness-native independent refutation pass at full tier with external CLIs as optional upgrade only (new ensure-8), /work no-arg spec listing (ensure-7), checks 7-9 added. Awaiting Jake's acceptance.

## Teardown (on acceptance of the built work)

Archive this spec to `~/.claude/specs/done/`; move retired skills to `~/.claude/skills-retired/`; run one real task through `/work` as the pilot and append the friction log to this spec's Status before archiving.
