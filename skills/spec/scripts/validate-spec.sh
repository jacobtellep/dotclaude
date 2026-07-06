#!/bin/bash
# validate-spec.sh <spec-file> — machine check of the reconciler spec format.
# Exits non-zero naming each violation. Format drift is caught here, not by hope.
set -u
f="${1:-}"
[ -n "$f" ] && [ -f "$f" ] || { echo "usage: validate-spec.sh <spec-file>"; exit 2; }
rc=0
fail() { echo "VIOLATION: $1"; rc=1; }

# 1. Eight required elements present.
grep -qiE '^spec-version:' "$f" || fail "missing 'spec-version:' stamp"
grep -qiE '^## Intent' "$f" || fail "missing '## Intent'"
grep -qiE '^## Desired [Ss]tate' "$f" || fail "missing '## Desired State'"
grep -qiE '^## Acceptance [Cc]hecks' "$f" || fail "missing '## Acceptance Checks'"
grep -qiE '^## Non-goals' "$f" || fail "missing '## Non-goals & Ownership'"
grep -qiE '^## Acceptance [Pp]rotocol' "$f" || fail "missing '## Acceptance Protocol'"
grep -qiE '^## Status' "$f" || fail "missing '## Status'"
grep -qiE '^## Teardown' "$f" || fail "missing '## Teardown'"

# 2. Every numbered Desired State line starts with "Ensure".
in_ds=0
bad_lines=0
ensures=0
while IFS= read -r line; do
  case "$line" in
    '## Desired '[Ss]tate*) in_ds=1; continue ;;
    '## '*) in_ds=0 ;;
  esac
  if [ "$in_ds" = 1 ] && printf '%s' "$line" | grep -qE '^[0-9]+\.'; then
    if printf '%s' "$line" | grep -qE '^[0-9]+\.[[:space:]]+\**[Ee]nsure'; then
      ensures=$((ensures+1))
    else
      bad_lines=$((bad_lines+1))
      fail "Desired State line does not start with 'Ensure': ${line%%.*}."
    fi
  fi
done < "$f"
[ "$ensures" -gt 0 ] || fail "Desired State has no numbered 'Ensure' lines"

# 3. Check table has at least one row per criterion.
checks=$(awk '/^## Acceptance [Cc]hecks/{flag=1;next}/^## /{flag=0}flag' "$f" | grep -cE '^\|[[:space:]]*[0-9]+[[:space:]]*\|')
if [ "$checks" -lt "$ensures" ]; then
  fail "only $checks check row(s) for $ensures criteria — every 'Ensure' needs a check"
fi

[ "$rc" = 0 ] && echo "OK: $f ($ensures criteria, $checks checks)"
exit "$rc"
