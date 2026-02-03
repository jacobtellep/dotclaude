#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
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
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

# Load environment variables
load_dotenv()

def main():
    """
    Progress Checkpoint Hook - Pauses every 2 file changes for user approval
    
    This hook tracks file modifications and forces a checkpoint every 2 changes,
    showing the user what has been done and asking for permission to continue.
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
    
    # Track file changes
    change_count = track_file_change(file_path)
    
    # Check if we've hit the checkpoint (every 2 changes)
    if change_count % 2 == 0 and change_count > 0:
        # Show progress and request approval
        show_progress_checkpoint(change_count)
        
        # Block execution - user must approve to continue
        response = {
            "action": "block",
            "reason": f"🛑 Progress Checkpoint #{change_count//2}!\n\nI've made {change_count} file changes. Here's what I've done:\n\n" + get_recent_changes() + "\n\nShould I continue? (yes/no)\nOr type 'skip-checkpoints' to disable for this session."
        }
        
        print(json.dumps(response))
        sys.exit(0)
    
    # Not a checkpoint, continue
    print(json.dumps({"action": "approve"}))
    sys.exit(0)

def is_code_file(file_path):
    """Check if file is a code file that should be tracked"""
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

def track_file_change(file_path):
    """Track file changes and return current count"""
    markers = log_utils.markers_dir()

    # Check if checkpoints are disabled
    skip_file = markers / ".skip_checkpoints"
    if skip_file.exists():
        return 0

    # Load or create tracking file
    tracking_file = markers / ".progress_tracking.json"
    
    if tracking_file.exists():
        try:
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
        except:
            tracking_data = {"changes": [], "count": 0}
    else:
        tracking_data = {"changes": [], "count": 0}
    
    # Add this change
    change_entry = {
        "timestamp": datetime.now().isoformat(),
        "file_path": file_path,
        "change_number": tracking_data["count"] + 1
    }
    
    tracking_data["changes"].append(change_entry)
    tracking_data["count"] += 1
    
    # Keep only last 10 changes
    if len(tracking_data["changes"]) > 10:
        tracking_data["changes"] = tracking_data["changes"][-10:]
    
    # Write back to file
    try:
        with open(tracking_file, 'w') as f:
            json.dump(tracking_data, f, indent=2)
    except:
        pass  # Don't fail if tracking fails
    
    return tracking_data["count"]

def show_progress_checkpoint(change_count):
    """Show progress information to user via stderr"""
    print(f"\n🛑 Progress Checkpoint #{change_count//2}!", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"FILE CHANGES: {change_count} files modified", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    # Show recent changes
    recent_changes = get_recent_changes_detailed()
    print(recent_changes, file=sys.stderr)
    
    print("\n" + "="*60, file=sys.stderr)
    print("CHECKPOINT ACTIONS:", file=sys.stderr)
    print("- Type 'yes' to continue", file=sys.stderr)
    print("- Type 'no' to stop", file=sys.stderr)
    print("- Type 'skip-checkpoints' to disable for this session", file=sys.stderr)
    print("="*60, file=sys.stderr)

def get_recent_changes():
    """Get summary of recent changes for the block message"""
    tracking_file = log_utils.markers_dir() / ".progress_tracking.json"
    
    if not tracking_file.exists():
        return "No changes tracked yet."
    
    try:
        with open(tracking_file, 'r') as f:
            tracking_data = json.load(f)
    except:
        return "Unable to read change history."
    
    changes = tracking_data.get("changes", [])
    if not changes:
        return "No changes recorded."
    
    # Get last 4 changes
    recent = changes[-4:]
    
    summary = []
    for change in recent:
        file_path = change["file_path"]
        change_num = change["change_number"]
        summary.append(f"  {change_num}. {file_path}")
    
    return "\n".join(summary)

def get_recent_changes_detailed():
    """Get detailed view of recent changes for stderr output"""
    tracking_file = log_utils.markers_dir() / ".progress_tracking.json"
    
    if not tracking_file.exists():
        return "No changes tracked yet."
    
    try:
        with open(tracking_file, 'r') as f:
            tracking_data = json.load(f)
    except:
        return "Unable to read change history."
    
    changes = tracking_data.get("changes", [])
    if not changes:
        return "No changes recorded."
    
    # Get last 6 changes
    recent = changes[-6:]
    
    output = []
    for change in recent:
        file_path = change["file_path"]
        change_num = change["change_number"]
        timestamp = change["timestamp"]
        
        # Parse timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = "unknown"
        
        output.append(f"  {change_num:2d}. {file_path} [{time_str}]")
    
    return "\n".join(output)

if __name__ == "__main__":
    main()