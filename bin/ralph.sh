#!/bin/bash
# ralph.sh — phase-separated overnight agent loop with a verification reject-gate.
#
#   ralph.sh --prompt PROMPT.md [--engine claude|codex] [--max-iter 8]
#            [--verify <script>] [--logdir .ralph] [--timeout-min 20]
#
# Each iteration: feed PROMPT.md (+ state + last failures) to the agent, then run
# the verify script. FAIL output is fed into the next iteration's prompt. Stops on
# all-pass, stuck diff, or max iterations.
#
# Conventions for PROMPT.md (the loop works best when it follows these):
#   - ONE task per iteration. State which task you picked and why.
#   - Write a failing test for the acceptance criteria FIRST, then make it pass —
#     the verify gate only has teeth if the work is test-covered.
#   - Search before building. Do NOT assume a feature isn't implemented yet.
#   - Track per-task status in .ralph/status.json: {"tasks":{"<name>":{"status":
#     "pending|in-progress|failing|passed|known-issue","attempts":N,"notes":"why
#     the last attempt failed / what to try differently"}}}. After 3 failed
#     attempts on a task, mark it known-issue and move on.
#
# Run this inside a dedicated git worktree — it invokes the agent with
# permissions skipped. No browser verification in-loop; cover UI behavior with
# Playwright tests that the verify script runs.
set -u

PROMPT=""
ENGINE="claude"
MAX_ITER=8
VERIFY=""
LOGDIR=".ralph"
TIMEOUT_MIN=20

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt)      PROMPT="$2"; shift ;;
    --engine)      ENGINE="$2"; shift ;;
    --max-iter)    MAX_ITER="$2"; shift ;;
    --verify)      VERIFY="$2"; shift ;;
    --logdir)      LOGDIR="$2"; shift ;;
    --timeout-min) TIMEOUT_MIN="$2"; shift ;;
    *) echo "ralph.sh: unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done

[ -n "$PROMPT" ] && [ -f "$PROMPT" ] || { echo "ralph.sh: --prompt <file> is required" >&2; exit 64; }
case "$ENGINE" in claude|codex) ;; *) echo "ralph.sh: --engine must be claude or codex" >&2; exit 64 ;; esac

if [ -z "$VERIFY" ]; then
  if [ -x "./scripts/verify.sh" ]; then VERIFY="./scripts/verify.sh"
  else VERIFY="$HOME/.claude/skills/check-code/scripts/verify.sh"; fi
fi

# Warn when not in a worktree (primary checkout + skipped permissions = risky).
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo "")
case "$GIT_DIR" in
  *worktrees*) ;;
  "") echo "ralph.sh: WARNING — not a git repository" >&2 ;;
  *) echo "ralph.sh: WARNING — this looks like a primary checkout, not a worktree. Consider running in a dedicated worktree." >&2 ;;
esac

mkdir -p "$LOGDIR"
PREV_HASH=""
LAST_VERIFY=""

for i in $(seq 1 "$MAX_ITER"); do
  echo "=== ralph iteration $i/$MAX_ITER ($(date '+%H:%M:%S')) ==="

  ITER_PROMPT="$LOGDIR/iter-$i.prompt"
  {
    cat "$PROMPT"
    if [ -f "$LOGDIR/status.json" ]; then
      echo; echo "--- CURRENT TASK STATE (.ralph/status.json) ---"
      cat "$LOGDIR/status.json"
    fi
    if [ "$i" -gt 1 ] && [ -n "$LAST_VERIFY" ]; then
      echo; echo "--- PREVIOUS ITERATION'S VERIFICATION ---"
      echo "$LAST_VERIFY"
      for f in "$LOGDIR"/last-fail-*.log; do
        [ -f "$f" ] && { echo "--- $(basename "$f") (tail) ---"; tail -40 "$f"; }
      done
      echo
      echo "Fix these failures with the smallest change that turns FAIL to PASS."
      echo "If this is your 3rd attempt on the same task, mark it known-issue in status.json and pick the next task."
    fi
  } > "$ITER_PROMPT"

  TIMEOUT_SEC=$((TIMEOUT_MIN * 60))
  if [ "$ENGINE" = "claude" ]; then
    perl -e 'alarm shift; exec @ARGV' "$TIMEOUT_SEC" \
      claude -p "$(cat "$ITER_PROMPT")" --dangerously-skip-permissions \
      > "$LOGDIR/iter-$i.out" 2>&1
  else
    perl -e 'alarm shift; exec @ARGV' "$TIMEOUT_SEC" \
      codex exec --full-auto "$(cat "$ITER_PROMPT")" \
      > "$LOGDIR/iter-$i.out" 2>&1
  fi
  AGENT_EXIT=$?
  [ $AGENT_EXIT -eq 142 ] && echo "  agent timed out after ${TIMEOUT_MIN}m" | tee -a "$LOGDIR/iter-$i.out"

  # Verification gate
  VERIFY_OUT=$(bash "$VERIFY" --quiet 2>/dev/null)
  VERIFY_EXIT=$?
  LAST_VERIFY=$(echo "$VERIFY_OUT" | grep '^VERIFY')
  echo "$LAST_VERIFY" | tee "$LOGDIR/iter-$i.verify"

  # Stash failing logs for the next prompt
  rm -f "$LOGDIR"/last-fail-*.log
  VLOGDIR=$(echo "$VERIFY_OUT" | grep '^VERIFY_LOGS:' | cut -d' ' -f2)
  if [ $VERIFY_EXIT -ne 0 ] && [ -n "$VLOGDIR" ]; then
    for check in lint typecheck test; do
      echo "$LAST_VERIFY" | grep -q "$check=FAIL" && [ -f "$VLOGDIR/verify-$check.log" ] \
        && cp "$VLOGDIR/verify-$check.log" "$LOGDIR/last-fail-$check.log"
    done
  fi

  if [ $VERIFY_EXIT -eq 0 ]; then
    echo "=== ralph: all checks pass after $i iteration(s) ==="
    exit 0
  fi

  # Stuck detection: agent produced no new diff
  HASH=$(git diff HEAD 2>/dev/null | shasum | cut -d' ' -f1)
  if [ -n "$PREV_HASH" ] && [ "$HASH" = "$PREV_HASH" ]; then
    echo "=== ralph: STUCK — no new changes in iteration $i. Stopping. ===" >&2
    exit 2
  fi
  PREV_HASH="$HASH"
done

echo "=== ralph: max iterations ($MAX_ITER) exhausted. Last: $LAST_VERIFY ===" >&2
exit 3
