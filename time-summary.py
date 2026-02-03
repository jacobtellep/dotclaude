#!/usr/bin/env python3
"""Generate daily/weekly time-tracking summaries from Claude Code logs."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
HISTORY_FILE = CLAUDE_DIR / "history.jsonl"
PROJECT_LOGS_DIR = CLAUDE_DIR / "project-logs"
STATS_CACHE_FILE = CLAUDE_DIR / "stats-cache.json"
DEFAULT_GAP_MINUTES = 30


def parse_args():
    parser = argparse.ArgumentParser(description="Claude Code time summary")
    parser.add_argument("--date", help="Show summary for a specific date (YYYY-MM-DD)")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--week", action="store_true", help="Show current Mon-Fri week")
    parser.add_argument(
        "--gap",
        type=int,
        default=DEFAULT_GAP_MINUTES,
        help=f"Inactivity gap in minutes to split sessions (default: {DEFAULT_GAP_MINUTES})",
    )
    args = parser.parse_args()

    today = datetime.now().date()

    if args.week:
        # Monday of this week
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        return monday, min(friday, today), args.gap
    elif args.date:
        d = datetime.strptime(args.date, "%Y-%m-%d").date()
        return d, d, args.gap
    elif args.from_date and args.to_date:
        start = datetime.strptime(args.from_date, "%Y-%m-%d").date()
        end = datetime.strptime(args.to_date, "%Y-%m-%d").date()
        return start, end, args.gap
    else:
        return today, today, args.gap


def parse_history(start_date, end_date):
    """Read history.jsonl and return entries within the date range."""
    entries = []
    start_ts = datetime.combine(start_date, datetime.min.time()).timestamp() * 1000
    end_ts = (
        datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)
    ).timestamp() * 1000

    if not HISTORY_FILE.exists():
        return entries

    with open(HISTORY_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("timestamp", 0)
            if start_ts <= ts < end_ts:
                entries.append(entry)

    entries.sort(key=lambda e: e["timestamp"])
    return entries


def find_project_log_dir(project_path):
    """Map project path to its project-logs directory."""
    name = Path(project_path).name
    h = hashlib.sha256(project_path.encode()).hexdigest()[:8]
    log_dir = PROJECT_LOGS_DIR / f"{name}_{h}"
    return log_dir if log_dir.exists() else None


def parse_file_modifications(log_dir, start_date, end_date):
    """Parse file_modifications.log and return entries within range."""
    mods = []
    log_file = log_dir / "file_modifications.log"
    if not log_file.exists():
        return mods

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (\w+): (.+)$")

    with open(log_file) as f:
        for line in f:
            m = pattern.match(line.strip())
            if not m:
                continue
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            if start_dt <= ts < end_dt:
                mods.append(
                    {"timestamp": ts, "action": m.group(2), "path": m.group(3)}
                )
    return mods


def load_stats_cache(start_date, end_date):
    """Load daily aggregates from stats-cache.json."""
    totals = {"messageCount": 0, "sessionCount": 0, "toolCallCount": 0}
    if not STATS_CACHE_FILE.exists():
        return totals

    with open(STATS_CACHE_FILE) as f:
        data = json.load(f)

    for day in data.get("dailyActivity", []):
        d = datetime.strptime(day["date"], "%Y-%m-%d").date()
        if start_date <= d <= end_date:
            totals["messageCount"] += day.get("messageCount", 0)
            totals["sessionCount"] += day.get("sessionCount", 0)
            totals["toolCallCount"] += day.get("toolCallCount", 0)
    return totals


def cluster_into_sessions(entries, file_mods, gap_minutes):
    """Group entries by project and split into sessions by time gap."""
    by_project = defaultdict(list)
    for entry in entries:
        project = entry.get("project", "unknown")
        by_project[project].append(entry)

    all_sessions = []
    for project, proj_entries in by_project.items():
        proj_entries.sort(key=lambda e: e["timestamp"])
        sessions = []
        current = [proj_entries[0]]

        for entry in proj_entries[1:]:
            gap = (entry["timestamp"] - current[-1]["timestamp"]) / 60000
            if gap > gap_minutes:
                sessions.append(current)
                current = [entry]
            else:
                current.append(entry)
        sessions.append(current)

        for session_entries in sessions:
            start_ts = session_entries[0]["timestamp"] / 1000
            end_ts = session_entries[-1]["timestamp"] / 1000
            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)

            # Count file modifications within this session's time window
            # Extend window slightly to catch modifications triggered by the last message
            window_start = start_dt - timedelta(minutes=1)
            window_end = end_dt + timedelta(minutes=5)
            session_files = set()
            for mod in file_mods.get(project, []):
                if window_start <= mod["timestamp"] <= window_end:
                    path = mod["path"]
                    if "/.claude/" not in path:
                        session_files.add(path)

            # Get first substantive message for description
            description = ""
            for e in session_entries:
                msg = e.get("display", "").strip()
                if msg and len(msg) > 5:
                    description = msg
                    break

            all_sessions.append(
                {
                    "project": project,
                    "start": start_dt,
                    "end": end_dt,
                    "messages": session_entries,
                    "file_count": len(session_files),
                    "description": description,
                }
            )

    all_sessions.sort(key=lambda s: s["start"])
    return all_sessions


def clean_project_name(path):
    """Convert project path to a readable name."""
    name = Path(path).name
    # Convert kebab-case and snake_case to Title Case
    name = re.sub(r"[-_]", " ", name)
    return name.title()


def format_duration(start, end):
    """Format a duration as '2h 19m' or '<1m'."""
    delta = end - start
    total_minutes = int(delta.total_seconds() / 60)
    if total_minutes < 1:
        return "<1m"
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def truncate(text, max_len=50):
    """Truncate text with ellipsis."""
    # Collapse whitespace and remove newlines
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_report(sessions, start_date, end_date, stats):
    """Build the full terminal report."""
    width = 64
    lines = []

    # Header
    if start_date == end_date:
        date_str = start_date.strftime("%A, %B %d, %Y")
        title = f"Time Summary: {date_str}"
    else:
        title = (
            f"Time Summary: {start_date.strftime('%b %d')} - "
            f"{end_date.strftime('%b %d, %Y')}"
        )

    lines.append("=" * width)
    lines.append(f"  {title}")
    lines.append("=" * width)

    if not sessions:
        lines.append("")
        lines.append("  No activity found for this period.")
        lines.append("")
        lines.append("=" * width)
        return "\n".join(lines)

    # Group sessions by project
    by_project = defaultdict(list)
    for s in sessions:
        by_project[s["project"]].append(s)

    # Sort projects by first session start time
    sorted_projects = sorted(by_project.items(), key=lambda x: x[1][0]["start"])

    total_duration = timedelta()
    total_sessions = 0
    total_files = 0

    for project, proj_sessions in sorted_projects:
        proj_name = clean_project_name(project)
        session_count = len(proj_sessions)
        total_sessions += session_count

        lines.append("")
        session_label = "session" if session_count == 1 else "sessions"
        header = f"  {proj_name}"
        right = f"{session_count} {session_label}"
        padding = width - len(header) - len(right) - 2
        lines.append(f"{header}{' ' * max(padding, 2)}{right}")
        lines.append(f"  {'-' * (width - 4)}")

        proj_duration = timedelta()
        proj_files = 0

        for s in proj_sessions:
            duration = s["end"] - s["start"]
            proj_duration += duration
            proj_files += s["file_count"]
            total_files += s["file_count"]

            start_time = s["start"].strftime("%H:%M")
            end_time = s["end"].strftime("%H:%M")
            dur_str = format_duration(s["start"], s["end"])
            files_str = f"{s['file_count']} file{'s' if s['file_count'] != 1 else ''}"
            desc = truncate(s["description"])

            # Format: "  09:01 - 11:21  (2h 19m)  6 files  description..."
            time_part = f"  {start_time} - {end_time}"
            dur_part = f"({dur_str})"
            detail = f"{time_part}  {dur_part:>9s}  {files_str:>8s}  {desc}"
            lines.append(detail)

        total_duration += proj_duration

        # Subtotal
        dur_fmt = format_duration(
            proj_sessions[0]["start"],
            proj_sessions[0]["start"] + proj_duration,
        )
        file_label = "file" if proj_files == 1 else "files"
        lines.append("")
        lines.append(
            f"  Subtotal: {dur_fmt} across {session_count} {session_label}, "
            f"{proj_files} {file_label}"
        )
        lines.append(f"  {'-' * (width - 4)}")

    # Daily total
    total_mins = int(total_duration.total_seconds() / 60)
    total_h = total_mins // 60
    total_m = total_mins % 60
    if total_h > 0:
        total_dur_str = f"{total_h}h {total_m:02d}m"
    else:
        total_dur_str = f"{total_m}m"

    session_label = "session" if total_sessions == 1 else "sessions"
    file_label = "file" if total_files == 1 else "files"

    label = "DAILY TOTAL" if start_date == end_date else "TOTAL"
    lines.append("")
    lines.append(
        f"  {label}: {total_dur_str} across {total_sessions} {session_label}, "
        f"{total_files} {file_label} modified"
    )

    if stats["messageCount"] > 0:
        lines.append(
            f"  {'':>12s}Messages: {stats['messageCount']}  |  "
            f"Tool calls: {stats['toolCallCount']}"
        )

    lines.append("=" * width)
    return "\n".join(lines)


def main():
    start_date, end_date, gap_minutes = parse_args()

    entries = parse_history(start_date, end_date)

    # Collect file modifications per project
    file_mods = {}
    seen_projects = set()
    for entry in entries:
        project = entry.get("project", "")
        if project and project not in seen_projects:
            seen_projects.add(project)
            log_dir = find_project_log_dir(project)
            if log_dir:
                mods = parse_file_modifications(log_dir, start_date, end_date)
                if mods:
                    file_mods[project] = mods

    sessions = cluster_into_sessions(entries, file_mods, gap_minutes) if entries else []
    stats = load_stats_cache(start_date, end_date)
    report = format_report(sessions, start_date, end_date, stats)
    print(report)


if __name__ == "__main__":
    main()
