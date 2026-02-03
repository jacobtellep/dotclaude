#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

# Load environment variables
load_dotenv()

def main():
    """
    Interactive Decision Hook - Presents implementation options before Write/Edit operations
    
    This hook intercepts Write/Edit/MultiEdit operations and presents the user with
    3 simple implementation options, forcing collaborative decision-making.
    """
    
    try:
        # Read request from stdin
        request = json.load(sys.stdin)
    except:
        # If no JSON input, approve and continue
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Extract tool and parameters
    tool_name = request.get("tool", "")
    params = request.get("params", {})
    
    # Only intercept file modification operations
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Check if this is a code file (not config/docs)
    file_path = params.get("file_path", "")
    if not is_code_file(file_path):
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Check if we should skip this decision (marker file exists)
    decision_marker = log_utils.markers_dir() / ".interactive_decision_skip"
    if decision_marker.exists():
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Present interactive decision to user
    present_decision_options(tool_name, params)
    
    # Block execution - user must make decision
    response = {
        "action": "block",
        "reason": "⚠️ Interactive Decision Required!\n\nI need to make an implementation decision. Here are your options:\n\nA) Start with the simplest possible approach\nB) Show me existing patterns in the codebase first\nC) Present 3 specific implementation options\n\nPlease respond with A, B, or C, or type 'skip' to proceed without this check."
    }
    
    print(json.dumps(response))
    sys.exit(0)

def is_code_file(file_path):
    """Check if file is a code file that should trigger interactive decisions"""
    if not file_path:
        return False
    
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs', 
        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj',
        '.html', '.css', '.scss', '.sass', '.vue', '.svelte'
    }
    
    # Skip common non-code files
    skip_patterns = [
        '.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.toml',
        '.env', '.gitignore', '.dockerignore', 'README', 'LICENSE',
        '.claude/', 'logs/', '.git/'
    ]
    
    file_path_lower = file_path.lower()
    
    # Check if it's a skip pattern
    for pattern in skip_patterns:
        if pattern in file_path_lower:
            return False
    
    # Check if it has a code extension
    path_obj = Path(file_path)
    return path_obj.suffix.lower() in code_extensions

def present_decision_options(tool_name, params):
    """Present the decision options to the user via stderr"""
    file_path = params.get("file_path", "unknown")
    
    print(f"\n🎯 Interactive Decision Hook Triggered!", file=sys.stderr)
    print(f"Tool: {tool_name}", file=sys.stderr)
    print(f"File: {file_path}", file=sys.stderr)
    print("\n" + "="*50, file=sys.stderr)
    print("IMPLEMENTATION DECISION REQUIRED", file=sys.stderr)
    print("="*50, file=sys.stderr)
    
    if tool_name == "Write":
        print("\n📝 About to CREATE a new file.", file=sys.stderr)
    elif tool_name == "Edit":
        print("\n✏️  About to EDIT existing file.", file=sys.stderr)
    elif tool_name == "MultiEdit":
        print("\n🔄 About to make MULTIPLE edits.", file=sys.stderr)
    
    print("\nAs per CLAUDE.md guidelines, I must present options:", file=sys.stderr)
    print("\nA) Start with the simplest possible approach", file=sys.stderr)
    print("B) Show me existing patterns in the codebase first", file=sys.stderr)
    print("C) Present 3 specific implementation options", file=sys.stderr)
    print("\nOr type 'skip' to disable this check for this session.", file=sys.stderr)
    print("\n" + "="*50, file=sys.stderr)
    
    # Log the decision point
    log_decision_point(tool_name, file_path)

def log_decision_point(tool_name, file_path):
    """Log the decision point for tracking"""
    log_file = log_utils.log_dir() / "interactive_decisions.json"
    
    # Load existing log or create new
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        except:
            log_data = []
    else:
        log_data = []
    
    # Add new entry
    from datetime import datetime
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "file_path": file_path,
        "status": "decision_required"
    }
    
    log_data.append(entry)
    
    # Keep only last 100 entries
    if len(log_data) > 100:
        log_data = log_data[-100:]
    
    # Write back to file
    try:
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    except:
        pass  # Don't fail if logging fails

if __name__ == "__main__":
    main()