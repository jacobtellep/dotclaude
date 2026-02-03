"""
Shared utility for centralized Claude hook logging.

All hook log files, markers, and session data are written to:
    ~/.claude/project-logs/{project-slug}/

This prevents hooks from polluting project directories with logs/
and .claude/ files that would need to be .gitignored in every repo.
"""

import hashlib
import os
import re
from pathlib import Path


def _project_slug() -> str:
    """Return a unique, human-readable slug for the current project directory."""
    cwd = os.getcwd()
    name = os.path.basename(cwd) or "root"
    # Sanitize: lowercase, replace non-alphanum with hyphens, collapse runs
    name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
    short_hash = hashlib.sha256(cwd.encode()).hexdigest()[:8]
    return f"{name}_{short_hash}"


def _base_dir() -> Path:
    """Return the centralized project-log root for the current project."""
    return Path.home() / ".claude" / "project-logs" / _project_slug()


# ── Public helpers ────────────────────────────────────────────────

def log_dir() -> Path:
    """Return the centralized logs/ directory (JSON log files)."""
    d = _base_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def markers_dir() -> Path:
    """Return the centralized markers/ directory (state/skip files)."""
    d = _base_dir() / "markers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_summaries_dir() -> Path:
    """Return the centralized session_summaries/ directory."""
    d = _base_dir() / "session_summaries"
    d.mkdir(parents=True, exist_ok=True)
    return d


def project_log_file(name: str) -> Path:
    """Return path to a top-level log file (e.g. file_modifications.log)."""
    d = _base_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / name
