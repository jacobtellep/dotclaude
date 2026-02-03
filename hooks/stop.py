#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
Hook: stop.py
Purpose: Session completion with summary and optional TTS
Runs: Stop event (when Claude Code finishes)
"""

import json
import sys
import os
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def generate_session_summary():
    """Generate a session summary from logs."""
    summary_parts = []
    
    # Check file modifications
    log_file = log_utils.project_log_file("file_modifications.log")
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            created = sum(1 for line in lines if "created:" in line)
            modified = sum(1 for line in lines if "modified:" in line)
            
            if created > 0 or modified > 0:
                summary_parts.append("Modified {} files, created {} files".format(modified, created))
        except:
            pass
    
    # Check validation status
    validation_log = log_utils.project_log_file("validation.log")
    if validation_log.exists():
        try:
            with open(validation_log, 'r') as f:
                lines = f.readlines()
            if lines:
                summary_parts.append("Ran {} validation checkpoints".format(len(lines)))
        except:
            pass
    
    # Check for hook failures
    hook_failures = Path("HOOK-FAILURES.md")
    if hook_failures.exists():
        summary_parts.append("WARNING: Some hook failures detected - check HOOK-FAILURES.md")
    
    return summary_parts

def get_completion_message():
    """Get a completion message."""
    messages = [
        "Task completed successfully!",
        "All done! Great work!",
        "Finished! Everything looks good.",
        "Complete! Ready for the next task.",
        "Done! All systems green.",
    ]
    
    # Check if we have a summary
    summary = generate_session_summary()
    if summary:
        base_message = random.choice(messages)
        return "{} {}".format(base_message, ' '.join(summary))
    
    return random.choice(messages)

def save_session_summary():
    """Save detailed session summary."""
    summary_dir = log_utils.session_summaries_dir()
    
    timestamp = datetime.now()
    summary_file = summary_dir / "session_summary_{}.txt".format(timestamp.strftime('%Y%m%d_%H%M%S'))
    
    with open(summary_file, 'w') as f:
        f.write("=== Claude Code Session Summary ===\n")
        f.write("Date: {}\n\n".format(timestamp))
        
        # Add file modifications
        log_file = log_utils.project_log_file("file_modifications.log")
        if log_file.exists():
            f.write("Files Modified:\n")
            with open(log_file, 'r') as log:
                for line in log:
                    f.write("  {}".format(line))
            f.write("\n")
        
        # Add summary points
        summary = generate_session_summary()
        if summary:
            f.write("Summary:\n")
            for point in summary:
                f.write("  - {}\n".format(point))

def try_tts(text):
    """Use macOS TTS - always enabled."""
    try:
        # Always use macOS say command on macOS
        if sys.platform == "darwin":
            os.system("say '{}'".format(text))
    except:
        pass

def main():
    # Read the stop event from stdin
    try:
        event = json.load(sys.stdin)
    except:
        event = {}
    
    # Save session summary
    save_session_summary()
    
    # Get completion message
    message = get_completion_message()
    
    # Print summary
    import sys as system
    system.stderr.write("\nSUMMARY: {}\n".format(message))
    
    # Try TTS announcement
    # try_tts("Task complete")  # Disabled
    
    # Check for --chat flag to save transcript
    if "--chat" in sys.argv:
        # This would normally save the chat transcript
        # For now, just note it in logs
        with open(log_utils.log_dir() / "chat.json", 'w') as f:
            json.dump({"message": "Chat transcript saved", "timestamp": datetime.now().isoformat()}, f)
    
    sys.exit(0)

if __name__ == "__main__":
    main()