#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract current directory from JSON input
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')

# Change to the working directory if provided
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
    cd "$cwd"
fi

# Get git branch (skip locks to avoid hanging)
branch=$(git --no-optional-locks branch --show-current 2>/dev/null || echo "no-git")

# Get last commit time in a readable format
if [ "$branch" != "no-git" ]; then
    last_commit_time=$(git --no-optional-locks log -1 --format="%ar" 2>/dev/null || echo "no commits")
else
    last_commit_time="no repo"
fi

# Output the status line
printf "%s | %s" "$branch" "$last_commit_time"