---
description: Generate a time-tracking summary of Claude Code session activity
allowed-tools: Bash, Read
argument-hint: [today|yesterday|week|YYYY-MM-DD|YYYY-MM-DD YYYY-MM-DD]
---

Generate a time-tracking summary by running the time-summary.py script.

## Parse arguments from: $ARGUMENTS

Determine the correct flags based on the input:

- **No arguments or "today"** → run with no date flags (defaults to today)
- **"yesterday"** → calculate yesterday's date and use `--date YYYY-MM-DD`
- **"week"** → use `--week`
- **A single date like "2026-01-29"** → use `--date 2026-01-29`
- **Two dates like "2026-01-29 2026-01-30"** → use `--from 2026-01-29 --to 2026-01-30`
- **A day name like "friday" or "last monday"** → calculate the appropriate date and use `--date YYYY-MM-DD`

## Run the script

```bash
python3 ~/.claude/time-summary.py [FLAGS]
```

Display the full output to the user.

After showing results, let the user know they can ask to:
- Break down a specific project or session in more detail
- Adjust the session gap (e.g., "try with --gap 15")
- Look at a different date range
