#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
Hook: notification.py
Purpose: User notifications with optional TTS support
Runs: Notification events
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

# Personalized name for TTS messages
ENGINEER_NAME = "Jacob"

def log_notification(message):
    """Log notification to log file."""
    log_file = log_utils.log_dir() / "notification.log"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"

    # Append to log file
    with open(log_file, 'a') as f:
        f.write(log_entry)

def try_tts(text):
    """Use macOS TTS - always enabled."""
    try:
        # Always use macOS say command on macOS
        if sys.platform == "darwin":
            # Use devnull to suppress errors like the shell script
            os.system("say '{}' 2>/dev/null || true".format(text))
    except:
        # If TTS fails, just continue silently
        pass

def extract_tool_from_message(message):
    """Extract tool name from Claude permission message."""
    if "permission to use " in message:
        parts = message.split("permission to use ")
        if len(parts) > 1:
            tool_part = parts[1].strip()
            # Handle cases where there might be additional text after tool name
            tool_name = tool_part.split()[0] if tool_part else ""
            return tool_name
    return ""

def get_smart_message(message, enhanced_mode=False):
    """Generate smart, contextual notification messages."""
    if not enhanced_mode:
        return get_intervention_message(message)

    tool_name = extract_tool_from_message(message)

    # Tool-specific smart messaging
    if tool_name == "Bash":
        return f"Hey {ENGINEER_NAME}, Claude wants to run a command"
    elif tool_name == "Write":
        return f"{ENGINEER_NAME}, Claude is creating a new file"
    elif tool_name == "Edit" or tool_name == "MultiEdit":
        return f"{ENGINEER_NAME}, Claude wants to modify existing code"
    elif tool_name == "Read":
        return f"{ENGINEER_NAME}, Claude needs to read a file"
    elif tool_name in ["LS", "Glob", "Grep"]:
        return f"{ENGINEER_NAME}, Claude is exploring the codebase"
    elif tool_name == "Task":
        return f"{ENGINEER_NAME}, Claude is delegating to a subagent"
    elif tool_name == "TodoWrite":
        return f"{ENGINEER_NAME}, Claude is updating the task list"
    elif tool_name == "WebFetch" or tool_name == "WebSearch":
        return f"{ENGINEER_NAME}, Claude wants to search the internet"
    elif tool_name == "NotebookRead" or tool_name == "NotebookEdit":
        return f"{ENGINEER_NAME}, Claude is working with a Jupyter notebook"
    elif tool_name:
        return f"{ENGINEER_NAME}, Claude needs permission for {tool_name}"
    else:
        return f"Hey {ENGINEER_NAME}, your attention is required"

def get_intervention_message(message):
    """Generate appropriate TTS message based on notification content."""
    # Detect message type and generate appropriate response
    message_lower = message.lower()

    # Permission requests
    if "permission" in message_lower or "approve" in message_lower:
        return "The agent needs your permission"
    # Timeout/idle scenarios
    elif "idle" in message_lower or "timeout" in message_lower:
        return "The agent is idle or timed out"
    # Input requests
    elif "input" in message_lower or "waiting" in message_lower:
        return "The agent is waiting for your input"
    # General intervention
    else:
        return "Your attention is required"

def main():
    # Check for --notify flag (similar to how stop.py handles --chat)
    enhanced_mode = "--notify" in sys.argv

    # Read the notification from stdin
    try:
        notification = json.load(sys.stdin)
    except:
        sys.exit(0)

    message = notification.get("message", "")

    # Log the notification
    log_notification(message)

    # Also log to progress log
    progress_log = log_utils.project_log_file("progress.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(progress_log, 'a') as f:
        f.write("[{}] {}\n".format(timestamp, message))

    # Use smart messaging if enhanced mode is enabled
    if enhanced_mode:
        tts_message = get_smart_message(message, enhanced_mode=True)

        # Enhanced mode features
        tool_name = extract_tool_from_message(message)
        if tool_name:
            print(f"🔔 Enhanced Notification: {tool_name} tool requested", file=sys.stderr)

            # Add context-aware logging for enhanced mode
            enhanced_log = log_utils.log_dir() / "enhanced_notifications.json"

            enhanced_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "message": message,
                "smart_message": tts_message,
                "engineer": ENGINEER_NAME
            }

            # Read, append, write enhanced log
            enhanced_logs = []
            if enhanced_log.exists():
                try:
                    with open(enhanced_log, 'r') as f:
                        enhanced_logs = json.load(f)
                except:
                    enhanced_logs = []

            enhanced_logs.append(enhanced_entry)

            # Keep only last 100 enhanced notifications
            if len(enhanced_logs) > 100:
                enhanced_logs = enhanced_logs[-100:]

            with open(enhanced_log, 'w') as f:
                json.dump(enhanced_logs, f, indent=2)
    else:
        # Standard mode
        tts_message = get_intervention_message(message)

    try_tts(tts_message)

    # Also add visual alert (terminal bell) as backup
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except:
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()
