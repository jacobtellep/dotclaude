#!/bin/bash

# ANSI color codes
MAGENTA=$'\033[1;35m'
BADGE=$'\033[1;37;45m'       # bold white on magenta background
RED=$'\033[1;31m'
CYAN=$'\033[1;36m'
YELLOW=$'\033[1;33m'
DIM=$'\033[2m'
RESET=$'\033[0m'

# Read JSON input (required by Claude Code)
read -r json_input

# Get current directory from JSON or use pwd
cwd=$(echo "$json_input" | jq -r '.cwd // empty' 2>/dev/null)
cd "${cwd:-.}" 2>/dev/null || exit

# Check if in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "${MAGENTA}╔═${BADGE} ◆ CLAUDE ${MAGENTA}═╡${RESET} Not a git repo ${MAGENTA}║${RESET}"
    exit 0
fi

# Get repo name (from folder name at repo root)
repo=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")

# Get current branch (or short SHA if detached)
branch=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)

# Get time since last commit
last_commit=$(git log -1 --format=%ct 2>/dev/null)
if [ -n "$last_commit" ]; then
    now=$(date +%s)
    diff=$((now - last_commit))

    if [ $diff -lt 60 ]; then
        ago="${diff}s ago"
    elif [ $diff -lt 3600 ]; then
        ago="$((diff / 60))m ago"
    elif [ $diff -lt 86400 ]; then
        ago="$((diff / 3600))h ago"
    else
        ago="$((diff / 86400))d ago"
    fi
else
    ago="no commits"
fi

# Output the framed status line
echo "${MAGENTA}╔═${BADGE} ◆ CLAUDE ${MAGENTA}═╡${RESET} ${RED}${repo}${RESET} ${DIM}(${RESET}${CYAN}${branch}${RESET}${DIM})${RESET} ${DIM}│${RESET} ${YELLOW}${ago}${RESET} ${MAGENTA}║${RESET}"
