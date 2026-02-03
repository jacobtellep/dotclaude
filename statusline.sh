#!/bin/bash

# ANSI color codes using $'...' syntax for proper escape interpretation
RED=$'\033[1;31m'
CYAN=$'\033[1;36m'
YELLOW=$'\033[1;33m'
RESET=$'\033[0m'

# Read JSON input (required by Claude Code)
read -r json_input

# Get current directory from JSON or use pwd
cwd=$(echo "$json_input" | jq -r '.cwd // empty' 2>/dev/null)
cd "${cwd:-.}" 2>/dev/null || exit

# Check if in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "Not a git repo"
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

# Output the status line with colors
echo "${RED}${repo}${RESET} (${CYAN}${branch}${RESET}) - ${YELLOW}${ago}${RESET}"
