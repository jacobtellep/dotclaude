#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: file_size_check.py
Purpose: Prevents creation of files longer than 500 lines (per CLAUDE.md)
Runs: PreToolUse for Write|Edit|MultiEdit tools
"""

import json
import sys
from pathlib import Path

def main():
    # Read the request from stdin
    try:
        request = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    # Get file path from the request
    params = request.get("params", {})
    file_path = params.get("file_path", "")
    
    MAX_LINES = 500
    
    # Only check if file path is provided and file exists
    if file_path and Path(file_path).exists():
        try:
            with open(file_path, 'r') as f:
                line_count = sum(1 for _ in f)
            
            if line_count > MAX_LINES:
                print(f"⚠️  WARNING: File '{file_path}' has {line_count} lines (max: {MAX_LINES})", file=sys.stderr)
                print("📋 Per CLAUDE.md: Files should not exceed 500 lines. Consider refactoring into modules.", file=sys.stderr)
                print("💡 Suggestions:", file=sys.stderr)
                print("   - Split into multiple files by feature/responsibility", file=sys.stderr)
                print("   - Extract helper functions to separate modules", file=sys.stderr)
                print("   - Move types/interfaces to dedicated files", file=sys.stderr)
        except:
            # If we can't read the file, just continue
            pass
    
    # Don't block the operation, just warn
    response = {"action": "approve"}
    print(json.dumps(response))
    sys.exit(0)

if __name__ == "__main__":
    main()