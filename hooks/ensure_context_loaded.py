#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: ensure_context_loaded.py
Purpose: Ensures CLAUDE.md is loaded at the start of tasks
Runs: PreToolUse for all tools (via * matcher)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def main():
    # Define context files
    CLAUDE_FILE = Path("CLAUDE.md")
    CONTEXT_CHECK_FILE = log_utils.markers_dir() / ".context_loaded"

    # Check if this is a new session (context check file doesn't exist)
    if not CONTEXT_CHECK_FILE.exists():
        # Check if CLAUDE.md exists - warn but don't block
        if not CLAUDE_FILE.exists():
            print("⚠️  Note: CLAUDE.md not found in current directory", file=sys.stderr)
        else:
            print("✅ CLAUDE.md found. Remember to read it for development guidelines.", file=sys.stderr)

        # Create marker file to indicate context has been checked this session
        CONTEXT_CHECK_FILE.write_text(datetime.now().isoformat())

    # Exit successfully - never block
    sys.exit(0)

if __name__ == "__main__":
    main()