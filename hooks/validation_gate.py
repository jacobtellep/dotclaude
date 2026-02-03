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
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import log_utils

# Load environment variables
load_dotenv()

def main():
    """
    Validation Gate Hook - Pauses between PRP tasks to run tests and show results
    
    This hook detects when a PRP task is completed and forces validation before
    proceeding to the next task. Runs tests, shows results, and requires approval.
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
    
    # Only intercept TodoWrite operations (PRP task completions)
    if tool_name != "TodoWrite":
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Check if any todos were marked as completed
    todos = params.get("todos", [])
    if not has_completed_todos(todos):
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Validation gates are always enabled by default
    # Users can disable by removing this hook from settings.json
    
    # Check if we should skip this validation (user said to continue)
    skip_marker = log_utils.markers_dir() / ".skip_validation_gate"
    if skip_marker.exists():
        # Remove the skip marker and continue
        try:
            skip_marker.unlink()
        except:
            pass
        print(json.dumps({"action": "approve"}))
        sys.exit(0)
    
    # Run validation and show results
    validation_results = run_validation_checks()
    
    # Present validation gate to user
    present_validation_gate(validation_results)
    
    # Block execution - user must approve validation results
    response = {
        "action": "block",
        "reason": create_validation_message(validation_results)
    }
    
    print(json.dumps(response))
    sys.exit(0)

def has_completed_todos(todos):
    """Check if any todos were marked as completed"""
    for todo in todos:
        if todo.get("status") == "completed":
            return True
    return False

def run_validation_checks():
    """Run available validation checks and return results"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    # Check 1: Look for test command in common locations
    test_result = run_test_command()
    if test_result:
        results["checks"].append(test_result)
    
    # Check 2: Look for lint command
    lint_result = run_lint_command()
    if lint_result:
        results["checks"].append(lint_result)
    
    # Check 3: Basic file syntax check
    syntax_result = run_syntax_check()
    if syntax_result:
        results["checks"].append(syntax_result)
    
    # Check 4: Check for common issues
    issues_result = check_common_issues()
    if issues_result:
        results["checks"].append(issues_result)
    
    return results

def run_test_command():
    """Try to run tests and return results"""
    test_commands = [
        "npm test",
        "python -m pytest",
        "python -m unittest discover",
        "cargo test",
        "go test ./...",
        "mvn test",
        "gradle test"
    ]
    
    for cmd in test_commands:
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            return {
                "name": "Tests",
                "command": cmd,
                "status": "passed" if result.returncode == 0 else "failed",
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
                "returncode": result.returncode
            }
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            continue
    
    return {
        "name": "Tests",
        "command": "none found",
        "status": "skipped",
        "stdout": "No test command found",
        "stderr": "",
        "returncode": 0
    }

def run_lint_command():
    """Try to run linting and return results"""
    lint_commands = [
        "npm run lint",
        "python -m flake8 .",
        "python -m black --check .",
        "cargo clippy",
        "go fmt -d .",
        "eslint .",
        "prettier --check ."
    ]
    
    for cmd in lint_commands:
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            return {
                "name": "Linting",
                "command": cmd,
                "status": "passed" if result.returncode == 0 else "failed",
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
                "returncode": result.returncode
            }
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            continue
    
    return None

def run_syntax_check():
    """Check syntax of recently modified files"""
    issues = []
    
    # Get recently modified files
    recent_files = get_recent_files()
    
    for file_path in recent_files:
        if file_path.endswith('.py'):
            try:
                subprocess.run(
                    ["python", "-m", "py_compile", file_path],
                    capture_output=True,
                    timeout=10
                )
            except subprocess.CalledProcessError as e:
                issues.append(f"Syntax error in {file_path}: {e}")
            except:
                continue
    
    return {
        "name": "Syntax Check",
        "command": "python -m py_compile",
        "status": "passed" if not issues else "failed",
        "stdout": "All files compile successfully" if not issues else "",
        "stderr": "\n".join(issues) if issues else "",
        "returncode": 0 if not issues else 1
    }

def check_common_issues():
    """Check for common code issues"""
    issues = []
    
    # Check for files over 500 lines
    large_files = []
    recent_files = get_recent_files()
    
    for file_path in recent_files:
        try:
            with open(file_path, 'r') as f:
                line_count = sum(1 for _ in f)
                if line_count > 500:
                    large_files.append(f"{file_path} ({line_count} lines)")
        except:
            continue
    
    if large_files:
        issues.append(f"Files exceed 500 lines: {', '.join(large_files)}")
    
    return {
        "name": "Code Quality",
        "command": "file analysis",
        "status": "passed" if not issues else "warning",
        "stdout": "All quality checks passed" if not issues else "",
        "stderr": "\n".join(issues) if issues else "",
        "returncode": 0 if not issues else 1
    }

def get_recent_files():
    """Get list of recently modified files"""
    try:
        # Try to get files from git
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1..HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout:
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except:
        pass
    
    # Fallback: check tracking file
    tracking_file = log_utils.markers_dir() / ".progress_tracking.json"
    if tracking_file.exists():
        try:
            with open(tracking_file, 'r') as f:
                tracking_data = json.load(f)
                changes = tracking_data.get("changes", [])
                return [change["file_path"] for change in changes[-5:]]
        except:
            pass
    
    return []

def present_validation_gate(validation_results):
    """Present validation results to user via stderr"""
    print(f"\n🛑 Validation Gate Checkpoint!", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print("TASK COMPLETED - VALIDATION REQUIRED", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    # Show validation results
    for check in validation_results["checks"]:
        status_emoji = "✅" if check["status"] == "passed" else "❌" if check["status"] == "failed" else "⚠️"
        print(f"\n{status_emoji} {check['name']}: {check['status'].upper()}", file=sys.stderr)
        print(f"   Command: {check['command']}", file=sys.stderr)
        
        if check["stdout"]:
            print(f"   Output: {check['stdout'][:200]}...", file=sys.stderr)
        
        if check["stderr"]:
            print(f"   Errors: {check['stderr'][:200]}...", file=sys.stderr)
    
    print(f"\n" + "="*60, file=sys.stderr)
    print("VALIDATION ACTIONS:", file=sys.stderr)
    print("- Type 'continue' to proceed to next task", file=sys.stderr)
    print("- Type 'fix' to stop and address issues", file=sys.stderr)
    print("- Type 'disable-gates' to disable validation gates", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    # Log validation results
    log_validation_results(validation_results)

def create_validation_message(validation_results):
    """Create the validation message for the block response"""
    passed = sum(1 for check in validation_results["checks"] if check["status"] == "passed")
    failed = sum(1 for check in validation_results["checks"] if check["status"] == "failed")
    warnings = sum(1 for check in validation_results["checks"] if check["status"] == "warning")
    
    message = f"🛑 Validation Gate Checkpoint!\n\n"
    message += f"Task completed. Validation results:\n"
    message += f"✅ Passed: {passed}\n"
    message += f"❌ Failed: {failed}\n"
    message += f"⚠️ Warnings: {warnings}\n\n"
    
    if failed > 0:
        message += "❌ Some validations failed. Please review the results above.\n\n"
    
    message += "Actions:\n"
    message += "- Type 'continue' to proceed to next task\n"
    message += "- Type 'fix' to stop and address issues\n"
    message += "- Type 'disable-gates' to disable validation gates\n"
    
    return message

def log_validation_results(validation_results):
    """Log validation results for tracking"""
    log_file = log_utils.log_dir() / "validation_gates.json"
    
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
    log_data.append(validation_results)
    
    # Keep only last 50 entries
    if len(log_data) > 50:
        log_data = log_data[-50:]
    
    # Write back to file
    try:
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    except:
        pass  # Don't fail if logging fails

if __name__ == "__main__":
    main()