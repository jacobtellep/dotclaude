#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""
Hook: subagent_stop.py
Purpose: Simple subagent completion notification
Runs: SubagentStop event
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def log_subagent_completion():
    """Log subagent completion."""
    log_file = log_utils.log_dir() / "subagent_stop.json"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "subagent_complete"
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

def try_tts(text):
    """Try to use TTS if available."""
    try:
        # Method 1: macOS say command
        if sys.platform == "darwin":
            os.system(f'say "{text}"')
            return

        # Method 2: Linux espeak
        if sys.platform.startswith("linux"):
            os.system(f'espeak "{text}" 2>/dev/null')
            return

        # Method 3: Windows SAPI
        if sys.platform == "win32":
            import subprocess
            subprocess.run([
                "powershell", "-Command",
                f'Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{text}")'
            ], capture_output=True)
            return
    except:
        pass

def main():
    # Read the event from stdin
    try:
        event = json.load(sys.stdin)
    except:
        event = {}

    # Log the completion
    log_subagent_completion()

    # Simple notification
    print("✅ Subagent Complete", file=sys.stderr)

    # TTS announcement
    # try_tts("Subagent Complete")

    # Check for --chat flag
    if "--chat" in sys.argv:
        # Note in logs
        with open(log_utils.log_dir() / "chat.json", 'a') as f:
            f.write(json.dumps({
                "type": "subagent_complete",
                "timestamp": datetime.now().isoformat()
            }) + "\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
