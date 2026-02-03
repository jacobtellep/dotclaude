#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: pre_tool_use.py
Purpose: Security blocking for dangerous Bash commands
Runs: PreToolUse for Bash tool
"""

import json
import sys
import re


def is_dangerous_command(command):
    """Check for dangerous commands that should be blocked."""
    normalized = ' '.join(command.lower().split())

    # Block chmod 777
    if re.search(r'\bchmod\s+777', normalized):
        return True, "chmod 777 is dangerous - it gives everyone full access"

    # Block dangerous dd commands targeting disk devices
    if re.search(r'\bdd\s+.*of=/dev/[sh]d[a-z]', normalized):
        return True, "Dangerous dd command targeting disk device"

    return False, ""


def main():
    try:
        request = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = request.get("tool_input", {})
    command = tool_input.get("command", "")

    is_dangerous, reason = is_dangerous_command(command)
    if is_dangerous:
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Security Block: {reason}\n\nThis command has been blocked for safety reasons."
            }
        }
        print(json.dumps(response))
        sys.exit(0)

    # Check for .env file access in commands
    if '.env' in command and '.env.sample' not in command:
        sys.stderr.write("Warning: Command references .env file\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
