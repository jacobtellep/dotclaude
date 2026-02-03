#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: reality_checkpoint.py
Purpose: Enforces validation at reality checkpoints per CLAUDE.md
Runs: PreToolUse for Bash tool
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def main():
    # Read the request from stdin
    try:
        request = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    # Get command from the request (tool_input is the correct field name)
    tool_input = request.get("tool_input", {})
    command = tool_input.get("command", "")
    
    # Define checkpoint triggers
    checkpoint_triggers = [
        "git commit",
        "git push",
        "npm publish",
        "cargo publish",
        "pip upload",
        "docker push",
        "deploy",
        "release",
        "merge"
    ]
    
    # Check if this command is a reality checkpoint
    is_checkpoint = False
    
    # Check for explicit checkpoint triggers
    for trigger in checkpoint_triggers:
        if trigger in command:
            is_checkpoint = True
            break
    
    # Also check for test/build/validation commands that indicate task completion
    if re.search(r"(test|spec|lint|format|typecheck|build).*\s+(&&|\|\||;|$)", command):
        is_checkpoint = True
    
    if is_checkpoint:
        print("🛑 Reality Checkpoint Detected!", file=sys.stderr)
        print("================================", file=sys.stderr)
        print("Per CLAUDE.md, stop and validate at these moments:", file=sys.stderr)
        print("", file=sys.stderr)
        print("✓ After implementing a complete feature", file=sys.stderr)
        print("✓ Before starting a new major component", file=sys.stderr)
        print("✓ When something feels wrong", file=sys.stderr)
        print("✓ Before declaring 'done'", file=sys.stderr)
        print("✓ WHEN HOOKS FAIL WITH ERRORS ❌", file=sys.stderr)
        print("", file=sys.stderr)
        print("Required validation commands:", file=sys.stderr)
        print("  [test-command]", file=sys.stderr)
        print("  [lint-command]", file=sys.stderr)
        print("  [format-command]", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Command detected: {command}", file=sys.stderr)
        print("", file=sys.stderr)
        print("⚠️  Ensure all validation passes before proceeding!", file=sys.stderr)
        print("================================", file=sys.stderr)
        
        # Log checkpoint
        validation_log = log_utils.project_log_file("validation.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(validation_log, 'a') as f:
            f.write(f"[{timestamp}] Reality checkpoint: {command}\n")
    
    # Always approve (this is just a reminder) - exit 0 with no JSON needed
    sys.exit(0)

if __name__ == "__main__":
    main()