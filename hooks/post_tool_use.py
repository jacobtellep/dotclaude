#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: post_tool_use.py
Purpose: Logging and processing after tool execution
Runs: PostToolUse for all tools
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def log_tool_result(request, tool_response):
    """Log tool execution results to JSON file."""
    log_file = log_utils.log_dir() / "post_tool_use.json"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": request.get("tool_name", ""),
        "params": request.get("tool_input", {}),
        "exit_code": tool_response.get("exit_code", 0) if isinstance(tool_response, dict) else 0,
        "stdout_length": len(tool_response.get("stdout", "")) if isinstance(tool_response, dict) else 0,
        "stderr_length": len(tool_response.get("stderr", "")) if isinstance(tool_response, dict) else 0
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
    
    # Keep only last 1000 entries to prevent unbounded growth
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    # Write back
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def log_file_modification(file_path, action):
    """Log file modifications for tracking."""
    log_file = log_utils.project_log_file("file_modifications.log")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {action}: {file_path}\n")

def main():
    # Read the request from stdin
    try:
        request = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    tool_name = request.get("tool_name", "")
    tool_input = request.get("tool_input", {})
    tool_response = request.get("tool_response", {})
    
    # Log all tool results
    log_tool_result(request, tool_response)
    
    # Track file modifications
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        if file_path:
            action = "created" if tool_name == "Write" else "modified"
            log_file_modification(file_path, action)
            
            # Also track in the validation system
            validation_log = log_utils.project_log_file("validation.log")
            with open(validation_log, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - File {action}: {file_path}\n")
    
    # Check for test-related files and remind about tests
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        if file_path and any(file_path.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx"]):
            # Skip test files themselves
            if not any(x in file_path for x in ["test", "spec", "__tests__"]):
                print("💡 Reminder: Consider creating tests for new features", file=sys.stderr)
                print(f"   Test file could be: tests/{Path(file_path).stem}_test{Path(file_path).suffix}", file=sys.stderr)
    
    # Always approve (post hooks can't block)
    sys.exit(0)

if __name__ == "__main__":
    main()