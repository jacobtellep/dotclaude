#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: pre_tool_use.py
Purpose: Security blocking and logging for all tool usage
Runs: PreToolUse for all tools
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    """
    # Normalize command by removing extra spaces and converting to lowercase
    normalized = ' '.join(command.lower().split())
    
    # Pattern 1: Standard rm -rf variations
    patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf, rm -fr, rm -Rf, etc.
        r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
        r'\brm\s+--recursive\s+--force',  # rm --recursive --force
        r'\brm\s+--force\s+--recursive',  # rm --force --recursive
        r'\brm\s+-r\s+.*-f',  # rm -r ... -f
        r'\brm\s+-f\s+.*-r',  # rm -f ... -r
    ]
    
    # Check for dangerous patterns
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True
    
    # Pattern 2: Check for rm with recursive flag targeting dangerous paths
    dangerous_paths = [
        r'/',  # Root directory
        r'/\*',  # Root with wildcard
        r'~',  # Home directory
        r'~/',  # Home directory path
        r'\$HOME',  # Home environment variable
        r'\.\.',  # Parent directory references
        r'\*',  # Wildcards in general rm -rf context
        r'\.',  # Current directory
        r'\.\s*$',  # Current directory at end of command
    ]
    
    if re.search(r'\brm\s+.*-[a-z]*r', normalized):
        for dangerous_path in dangerous_paths:
            if re.search(dangerous_path, normalized):
                return True
    
    # Pattern 3: sudo rm variations
    if re.search(r'\bsudo\s+rm\s+-', normalized) and re.search(r'-[a-z]*[rf]', normalized):
        return True
    
    return False

def is_dangerous_command(command):
    """Check for various dangerous commands."""
    normalized = ' '.join(command.lower().split())
    
    # Allow rm commands (previously blocked). Still log elsewhere if needed.
    
    # Check chmod 777
    if re.search(r'\bchmod\s+777', normalized):
        return True, "chmod 777 is dangerous - it gives everyone full access"
    
    # Check dangerous dd commands
    if re.search(r'\bdd\s+.*of=/dev/[sh]d[a-z]', normalized):
        return True, "Dangerous dd command targeting disk device"
    
    return False, ""

def check_env_file_access(file_path):
    """Check if trying to access .env file (but allow .env.sample)."""
    if file_path and '.env' in file_path and '.env.sample' not in file_path:
        return True
    return False

def log_tool_use(request, action, reason=""):
    """Log tool usage to JSON file."""
    log_file = log_utils.log_dir() / "pre_tool_use.json"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": request.get("tool_name", ""),
        "params": request.get("tool_input", {}),
        "action": action,
        "reason": reason
    }
    
    # Read existing logs
    logs = []
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
    
    # Append new log
    logs.append(log_entry)
    
    # Write back
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def main():
    # Read the request from stdin
    try:
        request = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    tool_name = request.get("tool_name", "")
    tool_input = request.get("tool_input", {})
    
    # Check Bash commands for security issues
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        is_dangerous, reason = is_dangerous_command(command)
        if is_dangerous:
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"🛡️ Security Block: {reason}\n\nThis command has been blocked for safety reasons."
                }
            }
            log_tool_use(request, "block", reason)
            print(json.dumps(response))
            sys.exit(0)
    
    # Check file access for .env files
    if tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        if check_env_file_access(file_path):
            # Allow .env access but record a warning for auditability
            log_tool_use(request, "warn", ".env file access attempted (allowed)")
    
    # Log approved actions
    log_tool_use(request, "approve")

    # Approve the action - exit 0 with no JSON needed for approval
    sys.exit(0)

if __name__ == "__main__":
    main()