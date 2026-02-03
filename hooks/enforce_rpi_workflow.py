#!/usr/bin/env -S /Users/jacobtellep/.local/bin/uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Hook: enforce_rpi_workflow.py
Purpose: Enforces Research → Plan → Implement workflow from CLAUDE.md
Runs: PreToolUse for Write|Edit|MultiEdit tools
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

def main():
    # Read the request from stdin
    try:
        request = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    # Get file path from the request
    tool_name = request.get("tool", "")
    params = request.get("params", {})
    file_path = params.get("file_path", "")
    
    # Define workflow markers
    PLANNING_MARKER = log_utils.markers_dir() / ".planning_done"
    RESEARCH_MARKER = log_utils.markers_dir() / ".research_done"
    
    # Code file extensions
    CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".rb", ".php"}
    
    # Check if this is a code file
    if file_path and any(file_path.endswith(ext) for ext in CODE_EXTENSIONS):
        # Check if this is a new implementation task
        if not RESEARCH_MARKER.exists() and not PLANNING_MARKER.exists():
            response = {
                "action": "block",
                "reason": "⚠️  CLAUDE.md Workflow Violation Detected!\n\n" +
                         "❌ You're attempting to write code without following Research → Plan → Implement\n\n" +
                         "Required workflow:\n" +
                         "1. 🔍 Research: Explore the codebase and understand existing patterns\n" +
                         "2. 📋 Plan: Create a detailed implementation plan and verify with the user\n" +
                         "3. 💻 Implement: Execute the plan with validation checkpoints\n\n" +
                         "Please say: 'Let me research the codebase and create a plan before implementing.'\n\n" +
                         "To mark research complete, create the research marker.\n" +
                         "To mark planning complete, create the planning marker."
            }
            print(json.dumps(response))
            sys.exit(0)
        
        # Check if research is done but planning isn't
        if RESEARCH_MARKER.exists() and not PLANNING_MARKER.exists():
            response = {
                "action": "block",
                "reason": "⚠️  Planning Required Before Implementation\n\n" +
                         "✅ Research phase completed\n" +
                         "❌ Planning phase not completed\n\n" +
                         "Please create and share your implementation plan with the user before coding.\n" +
                         "To mark planning complete, create the planning marker."
            }
            print(json.dumps(response))
            sys.exit(0)
    
    # If we get here, workflow is being followed correctly
    response = {"action": "approve"}
    print(json.dumps(response))
    sys.exit(0)

if __name__ == "__main__":
    main()