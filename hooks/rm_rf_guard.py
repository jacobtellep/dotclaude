#!/usr/bin/env python3
"""Require approval before recursive forced rm commands."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import shlex
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple


RM_COMMANDS = {"rm", "/bin/rm", "/usr/bin/rm"}
SHELL_COMMANDS = {"sh", "bash", "zsh"}
BOUNDARY_CHARS = set(";&|()<>`\n")
CONTROL_BOUNDARY_CHARS = BOUNDARY_CHARS - set("<>")
FD_PREFIX_START = "\x00fd:"
FD_PREFIX_END = "\x00"
SHELL_OPERATORS = (
    "&>>",
    ">>&",
    "<<<",
    ";;&",
    "&&",
    "||",
    "|&",
    "&>",
    ">|",
    ">>",
    "<<",
    "<>",
    ">&",
    "<&",
    ";;",
    ";&",
    ";",
    "|",
    "&",
    "(",
    ")",
    "<",
    ">",
    "`",
    "\n",
)
LITERAL_BOUNDARIES = {
    character: f"\x00{ord(character):02x}\x00" for character in BOUNDARY_CHARS
}
ARITHMETIC_PLACEHOLDER = "$\x00arithmetic\x00"
ASSIGNMENT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]\n]+\])?\+?="
)
APPROVAL = re.compile(r"^approve rm-rf ([0-9a-f]{32})$")
RAW_RM = re.compile(r"(?<![A-Za-z0-9_./-])(?:/bin/|/usr/bin/)?rm(?=$|[\s;&|()`])")
PENDING_TTL_SECONDS = 10 * 60
APPROVED_TTL_SECONDS = 2 * 60
CLOCK_BASIS_TOLERANCE_SECONDS = 5
LOCK_WAIT_SECONDS = 1
MAX_SUBSTITUTION_DEPTH = 64
STATE_VERSION = 2


class GuardError(RuntimeError):
    """Raised when approval state cannot be handled safely."""


@dataclass(frozen=True)
class Analysis:
    matched: bool
    canonical: bool


def _unshield(value: str) -> str:
    for character, placeholder in LITERAL_BOUNDARIES.items():
        value = value.replace(placeholder, character)
    return value


def _remove_line_continuations(command: str) -> str:
    output: List[str] = []
    quote: Optional[str] = None
    index = 0
    while index < len(command):
        character = command[index]
        if quote != "'" and command.startswith("$(", index) and not command.startswith(
            "$((", index
        ):
            end = _dollar_paren_end(command, index + 2)
            if end is None:
                output.append(character)
            else:
                output.append("$(")
                output.append(_remove_line_continuations(command[index + 2 : end]))
                output.append(")")
                index = end
        elif quote != "'" and character == "`":
            end = _backtick_end(command, index + 1)
            if end is None:
                output.append(character)
            else:
                output.append("`")
                output.append(_remove_line_continuations(command[index + 1 : end]))
                output.append("`")
                index = end
        elif quote == "'":
            output.append(character)
            if character == "'":
                quote = None
        elif command.startswith("\\\n", index):
            index += 1
        elif character == "\\":
            output.append(character)
            if index + 1 < len(command):
                index += 1
                output.append(command[index])
        else:
            output.append(character)
            if quote is None and character in {"'", '"'}:
                quote = character
            elif quote == '"' and character == '"':
                quote = None
        index += 1
    return "".join(output)


def _parameter_expansion_end(command: str, start: int) -> Optional[int]:
    depth = 1
    quote: Optional[str] = None
    escaped = False
    index = start
    while index < len(command):
        character = command[index]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif quote is not None:
            if command.startswith("$(", index):
                end = _dollar_paren_end(command, index + 2)
                if end is None:
                    return None
                index = end
            elif character == "`":
                end = _backtick_end(command, index + 1)
                if end is None:
                    return None
                index = end
            elif character in ")\n;&|" and character != quote:
                return None
            elif character == quote:
                quote = None
        elif character == "'":
            return None
        elif command.startswith("$(", index):
            end = _dollar_paren_end(command, index + 2)
            if end is None:
                return None
            index = end
        elif character == "`":
            end = _backtick_end(command, index + 1)
            if end is None:
                return None
            index = end
        elif character == '"':
            quote = character
        elif command.startswith("${", index):
            depth += 1
            index += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _arithmetic_end(command: str, start: int) -> Optional[int]:
    depth = 2
    quote: Optional[str] = None
    escaped = False
    index = start
    while index < len(command):
        character = command[index]
        if escaped:
            escaped = False
        elif quote == "'":
            if character == "'":
                quote = None
        elif quote == '"':
            if character == "\\":
                escaped = True
            elif character == '"':
                quote = None
            elif character == "`":
                end = _backtick_end(command, index + 1)
                if end is None:
                    return None
                index = end
            elif command.startswith("$(", index) and not command.startswith(
                "$((", index
            ):
                end = _dollar_paren_end(command, index + 2)
                if end is None:
                    return None
                index = end
            elif command.startswith("${", index):
                end = _parameter_expansion_end(command, index + 2)
                if end is None:
                    return None
                index = end
        elif character == "\\":
            escaped = True
        elif character in {"'", '"'}:
            quote = character
        elif character == "`":
            end = _backtick_end(command, index + 1)
            if end is None:
                return None
            index = end
        elif command.startswith("$(", index) and not command.startswith(
            "$((", index
        ):
            end = _dollar_paren_end(command, index + 2)
            if end is None:
                return None
            index = end
        elif command.startswith("${", index):
            end = _parameter_expansion_end(command, index + 2)
            if end is None:
                return None
            index = end
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _strip_comments(command: str) -> str:
    output: List[str] = []
    quote: Optional[str] = None
    escaped = False
    word_started = False
    index = 0
    while index < len(command):
        character = command[index]
        if escaped:
            if character == "\n":
                output.pop()
            elif character in BOUNDARY_CHARS:
                output.pop()
                output.append(LITERAL_BOUNDARIES[character])
                word_started = True
            else:
                output.append(character)
                word_started = True
            escaped = False
        elif quote == "'":
            if character == "'":
                output.append(character)
                quote = None
            else:
                output.append(LITERAL_BOUNDARIES.get(character, character))
        elif quote == '"':
            if character == "\\":
                output.append(character)
                escaped = True
            elif character == '"':
                output.append(character)
                quote = None
            elif command.startswith("$((", index):
                end = _arithmetic_end(command, index + 3)
                if end is None:
                    output.append(character)
                else:
                    output.append(ARITHMETIC_PLACEHOLDER)
                    index = end
            else:
                output.append(LITERAL_BOUNDARIES.get(character, character))
        elif character == "\\":
            output.append(character)
            escaped = True
        elif character in {"'", '"'}:
            output.append(character)
            quote = character
            word_started = True
        elif command.startswith("$((", index):
            end = _arithmetic_end(command, index + 3)
            if end is None:
                output.append(character)
                word_started = True
            else:
                output.append(ARITHMETIC_PLACEHOLDER)
                index = end
                word_started = True
        elif command.startswith("((", index):
            end = _arithmetic_end(command, index + 2)
            if end is None:
                output.append(character)
                word_started = False
            else:
                output.append(ARITHMETIC_PLACEHOLDER)
                index = end
                word_started = True
        elif character == "#" and not word_started:
            newline = command.find("\n", index)
            if newline == -1:
                break
            output.append("\n")
            index = newline
            word_started = False
        elif character.isdigit() and not word_started:
            end = index
            while end < len(command) and command[end].isdigit():
                end += 1
            if end < len(command) and command[end] in "<>":
                output.append(
                    f"{FD_PREFIX_START}{command[index:end]}{FD_PREFIX_END}"
                )
                index = end - 1
                word_started = True
            else:
                output.append(character)
                word_started = True
        else:
            output.append(character)
            word_started = not (
                character.isspace() or character in BOUNDARY_CHARS
            )
        index += 1
    return "".join(output)


def _tokens(command: str) -> List[str]:
    lexer = shlex.shlex(
        _strip_comments(command).strip(),
        posix=True,
        punctuation_chars=";&|()<>`\n",
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens: List[str] = []
    for token in lexer:
        if token and all(character in BOUNDARY_CHARS for character in token):
            remainder = token
            while remainder:
                operator = next(
                    (
                        candidate
                        for candidate in SHELL_OPERATORS
                        if remainder.startswith(candidate)
                    ),
                    remainder,
                )
                tokens.append(operator)
                remainder = remainder[len(operator) :]
        else:
            tokens.append(token)
    return tokens


def _backtick_end(command: str, start: int) -> Optional[int]:
    escaped = False
    for index in range(start, len(command)):
        character = command[index]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "`":
            return index
    return None


def _dollar_paren_end(command: str, start: int) -> Optional[int]:
    depth = 1
    quote: Optional[str] = None
    escaped = False
    word_started = False
    index = start
    while index < len(command):
        character = command[index]
        if escaped:
            escaped = False
            if character != "\n":
                word_started = True
        elif quote == "'":
            if character == "'":
                quote = None
        elif quote == '"':
            if character == "\\":
                escaped = True
            elif character == '"':
                quote = None
            elif character == "`":
                end = _backtick_end(command, index + 1)
                if end is None:
                    return None
                index = end
            elif command.startswith("$(", index):
                end = _dollar_paren_end(command, index + 2)
                if end is None:
                    return None
                index = end
        elif character == "\\":
            escaped = True
        elif character in {"'", '"'}:
            quote = character
            word_started = True
        elif character == "#" and not word_started:
            newline = command.find("\n", index)
            if newline == -1:
                return None
            index = newline
            word_started = False
        elif character == "`":
            end = _backtick_end(command, index + 1)
            if end is None:
                return None
            index = end
            word_started = True
        elif command.startswith("$(", index):
            end = _dollar_paren_end(command, index + 2)
            if end is None:
                return None
            index = end
            word_started = True
        elif character == "(":
            depth += 1
            word_started = False
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
            word_started = False
        else:
            word_started = not (
                character.isspace() or character in BOUNDARY_CHARS
            )
        index += 1
    return None


def _active_substitutions(command: str) -> Iterator[str]:
    quote: Optional[str] = None
    escaped = False
    word_started = False
    index = 0
    while index < len(command):
        character = command[index]
        if escaped:
            escaped = False
            if character != "\n":
                word_started = True
        elif quote == "'":
            if character == "'":
                quote = None
        elif quote == '"':
            if character == "\\":
                escaped = True
            elif character == '"':
                quote = None
            elif character == "`":
                end = _backtick_end(command, index + 1)
                if end is None:
                    return
                yield command[index + 1 : end]
                index = end
            elif command.startswith("$(", index) and not command.startswith(
                "$((", index
            ):
                end = _dollar_paren_end(command, index + 2)
                if end is None:
                    return
                yield command[index + 2 : end]
                index = end
        elif character == "\\":
            escaped = True
        elif character in {"'", '"'}:
            quote = character
            word_started = True
        elif character == "#" and not word_started:
            newline = command.find("\n", index)
            if newline == -1:
                return
            index = newline
            word_started = False
        elif character == "`":
            end = _backtick_end(command, index + 1)
            if end is None:
                return
            yield command[index + 1 : end]
            index = end
            word_started = True
        elif command.startswith("$(", index) and not command.startswith("$((", index):
            end = _dollar_paren_end(command, index + 2)
            if end is None:
                return
            yield command[index + 2 : end]
            index = end
            word_started = True
        else:
            word_started = not (
                character.isspace() or character in BOUNDARY_CHARS
            )
        index += 1


def _is_boundary(token: str) -> bool:
    return bool(token) and all(
        character in CONTROL_BOUNDARY_CHARS for character in token
    )


def _is_redirection(token: str) -> bool:
    return (
        bool(token)
        and any(character in "<>" for character in token)
        and all(character in "<>&|" for character in token)
    )


def _without_redirections(tokens: Sequence[str]) -> List[str]:
    result: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if (
            token.startswith(FD_PREFIX_START)
            and token.endswith(FD_PREFIX_END)
            and index + 1 < len(tokens)
            and _is_redirection(tokens[index + 1])
        ):
            index += 1
            continue
        if _is_redirection(token):
            index += 2
            continue
        result.append(token)
        index += 1
    return result


def _segments(tokens: Sequence[str]) -> Iterator[List[str]]:
    current: List[str] = []
    for token in tokens:
        if _is_boundary(token):
            if current:
                yield current
                current = []
        else:
            current.append(token)
    if current:
        yield current


def _skip_assignments(tokens: Sequence[str], index: int) -> int:
    while index < len(tokens) and ASSIGNMENT.match(tokens[index]):
        index += 1
    return index


def _skip_option_wrapper(
    tokens: Sequence[str],
    index: int,
    options_with_values: Sequence[str],
    joined_value_prefixes: Sequence[str] = (),
    short_value_options: str = "",
) -> int:
    index += 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if token in options_with_values:
            index += 2
            continue
        if any(token.startswith(prefix) and token != prefix for prefix in joined_value_prefixes):
            index += 1
            continue
        if token.startswith("-") and token != "-":
            if not token.startswith("--"):
                value_positions = [
                    position
                    for position, character in enumerate(token[1:])
                    if character in short_value_options
                ]
                if value_positions and value_positions[0] == len(token) - 2:
                    index += 2
                    continue
            index += 1
            continue
        return index
    return index


def _resolve_command(tokens: Sequence[str]) -> int:
    index = _skip_assignments(tokens, 0)
    for _ in range(8):
        if index >= len(tokens):
            return index
        name = Path(tokens[index]).name
        if name == "env":
            index = _skip_option_wrapper(
                tokens,
                index,
                (
                    "-u",
                    "--unset",
                    "-C",
                    "--chdir",
                    "-P",
                    "-S",
                    "--split-string",
                ),
                (
                    "-u",
                    "-C",
                    "-P",
                    "-S",
                    "--unset=",
                    "--chdir=",
                    "--split-string=",
                ),
                "uCPS",
            )
            index = _skip_assignments(tokens, index)
        elif name == "sudo":
            index = _skip_option_wrapper(
                tokens,
                index,
                (
                    "-u",
                    "--user",
                    "-g",
                    "--group",
                    "-h",
                    "--host",
                    "-p",
                    "--prompt",
                    "-C",
                    "--close-from",
                    "-D",
                    "--chdir",
                    "-R",
                    "--chroot",
                    "-T",
                    "--command-timeout",
                    "-r",
                    "--role",
                    "-t",
                    "--type",
                    "-U",
                    "--other-user",
                ),
                (
                    "--user=",
                    "--group=",
                    "--host=",
                    "--prompt=",
                    "--close-from=",
                    "--chdir=",
                    "--chroot=",
                    "--command-timeout=",
                    "--role=",
                    "--type=",
                    "--other-user=",
                ),
                "ughpCDRTrtU",
            )
        elif name == "command":
            index += 1
            while index < len(tokens) and tokens[index] in {"-p", "--"}:
                index += 1
            if index < len(tokens) and tokens[index] in {"-v", "-V"}:
                return len(tokens)
        elif name == "xargs":
            index = _skip_option_wrapper(
                tokens,
                index,
                (
                    "-a",
                    "--arg-file",
                    "-d",
                    "--delimiter",
                    "-E",
                    "-I",
                    "-J",
                    "-L",
                    "-n",
                    "--max-args",
                    "-P",
                    "--max-procs",
                    "-R",
                    "-S",
                    "-s",
                    "--max-chars",
                ),
                (
                    "-E",
                    "-I",
                    "-J",
                    "-L",
                    "-n",
                    "-P",
                    "-R",
                    "-S",
                    "-s",
                    "--eof=",
                    "--replace=",
                    "--max-lines=",
                    "--max-args=",
                    "--max-procs=",
                    "--max-chars=",
                ),
                "adEIJLnPRSs",
            )
        else:
            return index
        index = _skip_assignments(tokens, index)
    return len(tokens)


def _rm_options(arguments: Sequence[str]) -> Tuple[bool, List[str]]:
    recursive = False
    force = False
    operands: List[str] = []
    options_ended = False
    for argument in arguments:
        if not options_ended and argument == "--":
            options_ended = True
        elif not options_ended and argument.startswith("--"):
            recursive = recursive or argument == "--recursive"
            force = force or argument == "--force"
        elif not options_ended and argument.startswith("-") and argument != "-":
            flags = argument[1:]
            recursive = recursive or "r" in flags or "R" in flags
            force = force or "f" in flags
        else:
            operands.append(argument)
    return recursive and force, operands


def _shell_command_string(tokens: Sequence[str], command_index: int) -> Optional[str]:
    index = command_index + 1
    while index < len(tokens):
        option = tokens[index]
        if option == "--":
            return None
        if not option.startswith("-") or option == "-":
            return None
        if option.startswith("--"):
            if option in {"--init-file", "--rcfile"}:
                index += 2
            else:
                index += 1
            continue
        flags = option[1:]
        value_option = next(
            (
                position
                for position, character in enumerate(flags)
                if character in "oO"
            ),
            None,
        )
        command_option = flags.find("c")
        if command_option >= 0 and (
            value_option is None or command_option < value_option
        ):
            if index + 1 < len(tokens):
                return _unshield(tokens[index + 1])
            return None
        if value_option is not None and value_option == len(flags) - 1:
            index += 2
        else:
            index += 1
    return None


def _env_split_matches(segment: Sequence[str], command_index: int, depth: int) -> bool:
    if Path(segment[command_index]).name != "env" or depth >= 6:
        return False
    for index in range(command_index + 1, len(segment)):
        option = segment[index]
        short_options = option[1:] if option.startswith("-") and not option.startswith("--") else ""
        split_position = short_options.find("S")
        earlier_value_option = any(
            character in "uCP" for character in short_options[:split_position]
        )
        if option in {"-S", "--split-string"} and index + 1 < len(segment):
            expanded = _tokens(segment[index + 1])
            remainder = segment[index + 2 :]
        elif split_position >= 0 and not earlier_value_option:
            split_value = short_options[split_position + 1 :]
            if split_value:
                expanded = _tokens(split_value)
                remainder = segment[index + 1 :]
            elif index + 1 < len(segment):
                expanded = _tokens(segment[index + 1])
                remainder = segment[index + 2 :]
            else:
                continue
        elif option.startswith("--split-string="):
            expanded = _tokens(option.split("=", 1)[1])
            remainder = segment[index + 1 :]
        else:
            continue
        return _segment_matches([*segment[:index], *expanded, *remainder], depth + 1)
    return False


def _segment_matches(segment: Sequence[str], depth: int) -> bool:
    segment = _without_redirections(segment)
    if not segment:
        return False
    command_index = _resolve_command(segment)
    wrapper_index = _skip_assignments(segment, 0)
    if wrapper_index < len(segment) and _env_split_matches(segment, wrapper_index, depth):
        return True
    if command_index >= len(segment):
        return False
    command = segment[command_index]
    if command in RM_COMMANDS:
        matched, _ = _rm_options(segment[command_index + 1 :])
        return matched
    if Path(command).name in SHELL_COMMANDS and depth < 6:
        nested = _shell_command_string(segment, command_index)
        return bool(nested and analyze(nested, depth + 1).matched)
    if Path(command).name == "find":
        for index, token in enumerate(segment[command_index + 1 :], command_index + 1):
            if token in {"-exec", "-execdir"} and _segment_matches(segment[index + 1 :], depth + 1):
                return True
    return False


def _raw_candidate(command: str) -> bool:
    for match in RAW_RM.finditer(command):
        tail = re.split(r"[;&|)\n`]", command[match.end() :], maxsplit=1)[0]
        short_options = re.findall(r"(?<!\S)-([A-Za-z]+)(?=\s|$)", tail)
        recursive = "--recursive" in tail or any("r" in flags or "R" in flags for flags in short_options)
        force = "--force" in tail or any("f" in flags for flags in short_options)
        if recursive and force:
            return True
    return False


def _static_absolute_path(value: str) -> bool:
    value = _unshield(value)
    if not value.startswith("/"):
        return False
    return not any(character in value for character in "$*?[]{}~`\n")


def _canonical(tokens: Sequence[str]) -> bool:
    if not tokens or any(
        _is_boundary(token) or _is_redirection(token) for token in tokens
    ):
        return False
    if any(
        any(character in token for character in "$*?[]{}~`\n")
        for token in tokens
    ):
        return False
    if tokens[0] not in RM_COMMANDS:
        return False
    matched, operands = _rm_options(tokens[1:])
    return matched and bool(operands) and all(_static_absolute_path(operand) for operand in operands)


def analyze(command: str, depth: int = 0) -> Analysis:
    raw_command = command
    command = _remove_line_continuations(command)
    if depth < MAX_SUBSTITUTION_DEPTH:
        substitution_match = any(
            analyze(nested, depth + 1).matched
            for nested in _active_substitutions(command)
        )
    else:
        substitution_match = _raw_candidate(command)
    try:
        tokens = _tokens(command)
    except ValueError:
        return Analysis(
            matched=substitution_match or _raw_candidate(raw_command),
            canonical=False,
        )
    matched = substitution_match or any(
        _segment_matches(segment, depth) for segment in _segments(tokens)
    )
    return Analysis(matched=matched, canonical=matched and _canonical(tokens))


def _json_output(payload: Dict[str, object]) -> None:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def _decision(decision: str, reason: str) -> None:
    _json_output(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }
    )


def _state_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    root = base / "rm-rf-guard"
    try:
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        root_status = root.lstat()
    except OSError as exc:
        raise GuardError(f"cannot create approval state: {exc.strerror}") from exc
    if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        raise GuardError("approval state directory is not a real directory")
    try:
        root.chmod(0o700)
    except OSError as exc:
        raise GuardError(f"cannot secure approval state: {exc.strerror}") from exc
    return root


def _safe_open(path: Path, flags: int, mode: int = 0o600) -> int:
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        descriptor = os.open(path, flags, mode)
    except OSError as exc:
        raise GuardError(f"cannot open approval state: {exc.strerror}") from exc
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        os.close(descriptor)
        raise GuardError("approval state is not a regular file")
    os.fchmod(descriptor, 0o600)
    return descriptor


@contextmanager
def _session_lock(session_id: str) -> Iterator[Tuple[Path, Path]]:
    root = _state_root()
    session_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    lock_path = root / f"{session_hash}.lock"
    state_path = root / f"{session_hash}.json"
    descriptor = _safe_open(lock_path, os.O_RDWR | os.O_CREAT)
    locked = False
    try:
        deadline = _monotonic_time() + LOCK_WAIT_SECONDS
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except BlockingIOError as exc:
                if _monotonic_time() >= deadline:
                    raise GuardError("approval state lock is busy") from exc
                time.sleep(0.01)
        yield root, state_path
    except OSError as exc:
        raise GuardError(f"cannot lock approval state: {exc.strerror}") from exc
    finally:
        try:
            if locked:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _empty_state() -> Dict[str, object]:
    return {"version": STATE_VERSION, "records": {}}


def _load_state(path: Path) -> Dict[str, object]:
    try:
        descriptor = _safe_open(path, os.O_RDONLY)
    except GuardError as exc:
        try:
            path.lstat()
        except FileNotFoundError:
            return _empty_state()
        raise exc
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            state_value = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GuardError("approval state is corrupt") from exc
    if (
        not isinstance(state_value, dict)
        or set(state_value) != {"version", "records"}
        or state_value.get("version") != STATE_VERSION
    ):
        raise GuardError("approval state has an unsupported format")
    records = state_value.get("records")
    if not isinstance(records, dict) or not all(
        isinstance(key, str) and isinstance(value, dict)
        for key, value in records.items()
    ):
        raise GuardError("approval records are corrupt")
    return state_value


def _write_state(root: Path, path: Path, state_value: Dict[str, object]) -> None:
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", dir=root)
    except OSError as exc:
        raise GuardError(f"cannot create approval state: {exc.strerror}") from exc
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                state_value,
                handle,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except OSError as exc:
        raise GuardError(f"cannot write approval state: {exc.strerror}") from exc
    except ValueError as exc:
        raise GuardError("cannot write invalid approval state") from exc
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _records(state_value: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    records = state_value["records"]
    if not isinstance(records, dict):
        raise GuardError("approval records are corrupt")
    return records  # type: ignore[return-value]


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _validate_record(command_hash: str, record: Dict[str, object]) -> None:
    status_value = record.get("status")
    pending_fields = {
        "clock_offset",
        "command_hash",
        "created_at",
        "created_monotonic",
        "pending_expires_at",
        "pending_expires_monotonic",
        "status",
        "token",
    }
    approved_fields = pending_fields | {
        "approved_at",
        "approved_monotonic",
        "approved_expires_at",
        "approved_expires_monotonic",
    }
    expected_fields = approved_fields if status_value == "approved" else pending_fields
    if status_value not in {"pending", "approved"} or set(record) != expected_fields:
        raise GuardError("approval record is corrupt")
    if not re.fullmatch(r"[0-9a-f]{64}", command_hash):
        raise GuardError("approval record hash is corrupt")
    if record.get("command_hash") != command_hash:
        raise GuardError("approval record hash does not match its key")
    token = record.get("token")
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise GuardError("approval record token is corrupt")
    numeric_fields = {
        "clock_offset",
        "created_at",
        "created_monotonic",
        "pending_expires_at",
        "pending_expires_monotonic",
    }
    if status_value == "approved":
        numeric_fields |= {
            "approved_at",
            "approved_monotonic",
            "approved_expires_at",
            "approved_expires_monotonic",
        }
    if not all(_finite_number(record.get(field)) for field in numeric_fields):
        raise GuardError("approval record timestamps are corrupt")
    created_at = float(record["created_at"])
    created_monotonic = float(record["created_monotonic"])
    clock_offset = float(record["clock_offset"])
    pending_expires_at = float(record["pending_expires_at"])
    pending_expires_monotonic = float(record["pending_expires_monotonic"])
    if (
        abs((created_at - created_monotonic) - clock_offset)
        > CLOCK_BASIS_TOLERANCE_SECONDS
    ):
        raise GuardError("pending approval clock basis is corrupt")
    if not 0 < pending_expires_at - created_at <= PENDING_TTL_SECONDS:
        raise GuardError("pending approval lifetime is corrupt")
    if not 0 < pending_expires_monotonic - created_monotonic <= PENDING_TTL_SECONDS:
        raise GuardError("pending approval monotonic lifetime is corrupt")
    if status_value == "approved":
        approved_at = float(record["approved_at"])
        approved_monotonic = float(record["approved_monotonic"])
        approved_expires_at = float(record["approved_expires_at"])
        approved_expires_monotonic = float(record["approved_expires_monotonic"])
        if approved_monotonic < created_monotonic:
            raise GuardError("approved monotonic time is corrupt")
        if (
            abs((approved_at - approved_monotonic) - clock_offset)
            > CLOCK_BASIS_TOLERANCE_SECONDS
        ):
            raise GuardError("approved clock basis is corrupt")
        if not 0 < approved_expires_at - approved_at <= APPROVED_TTL_SECONDS:
            raise GuardError("approved lifetime is corrupt")
        if not 0 < approved_expires_monotonic - approved_monotonic <= APPROVED_TTL_SECONDS:
            raise GuardError("approved monotonic lifetime is corrupt")


def _validate_records(records: Dict[str, Dict[str, object]]) -> None:
    tokens = []
    for command_hash, record in records.items():
        _validate_record(command_hash, record)
        tokens.append(record["token"])
    if len(tokens) != len(set(tokens)):
        raise GuardError("approval record tokens are not unique")


def _record_expired(
    record: Dict[str, object], now_wall: float, now_monotonic: float
) -> bool:
    created_monotonic = float(record["created_monotonic"])
    current_offset = now_wall - now_monotonic
    if now_wall < float(record["created_at"]) or now_monotonic < created_monotonic:
        return True
    if abs(current_offset - float(record["clock_offset"])) > CLOCK_BASIS_TOLERANCE_SECONDS:
        return True
    if record["status"] == "approved":
        if (
            now_wall < float(record["approved_at"])
            or now_monotonic < float(record["approved_monotonic"])
        ):
            return True
        return (
            now_wall >= float(record["approved_expires_at"])
            or now_monotonic >= float(record["approved_expires_monotonic"])
        )
    return (
        now_wall >= float(record["pending_expires_at"])
        or now_monotonic >= float(record["pending_expires_monotonic"])
    )


def _cleanup(
    state_value: Dict[str, object], now_wall: float, now_monotonic: float
) -> bool:
    records = _records(state_value)
    _validate_records(records)
    expired = [
        key
        for key, record in records.items()
        if _record_expired(record, now_wall, now_monotonic)
    ]
    for key in expired:
        del records[key]
    return bool(expired)


def _command_hash(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def _monotonic_time() -> float:
    if hasattr(time, "clock_gettime") and hasattr(time, "CLOCK_MONOTONIC"):
        return time.clock_gettime(time.CLOCK_MONOTONIC)
    return time.monotonic()


def _new_token(records: Dict[str, Dict[str, object]]) -> str:
    existing = {record.get("token") for record in records.values()}
    while True:
        token = secrets.token_hex(16)
        if token not in existing:
            return token


def _pretool_state(session_id: str, command: str) -> Tuple[bool, Optional[str]]:
    now_wall = time.time()
    now_monotonic = _monotonic_time()
    command_hash = _command_hash(command)
    with _session_lock(session_id) as (root, path):
        state_value = _load_state(path)
        changed = _cleanup(state_value, now_wall, now_monotonic)
        records = _records(state_value)
        record = records.get(command_hash)
        if record and record.get("status") == "approved":
            del records[command_hash]
            _write_state(root, path, state_value)
            return True, None
        if record and record.get("status") == "pending":
            if changed:
                _write_state(root, path, state_value)
            token = record.get("token")
            if not isinstance(token, str):
                raise GuardError("approval record token is corrupt")
            return False, token
        token = _new_token(records)
        records[command_hash] = {
            "clock_offset": now_wall - now_monotonic,
            "command_hash": command_hash,
            "created_at": now_wall,
            "created_monotonic": now_monotonic,
            "pending_expires_at": now_wall + PENDING_TTL_SECONDS,
            "pending_expires_monotonic": now_monotonic + PENDING_TTL_SECONDS,
            "status": "pending",
            "token": token,
        }
        _write_state(root, path, state_value)
        return False, token


def _approve_token(session_id: str, token: str) -> bool:
    now_wall = time.time()
    now_monotonic = _monotonic_time()
    with _session_lock(session_id) as (root, path):
        state_value = _load_state(path)
        changed = _cleanup(state_value, now_wall, now_monotonic)
        matches = [
            record
            for record in _records(state_value).values()
            if record.get("status") == "pending" and record.get("token") == token
        ]
        if len(matches) != 1:
            if changed:
                _write_state(root, path, state_value)
            return False
        record = matches[0]
        record["status"] = "approved"
        record["approved_at"] = now_wall
        record["approved_monotonic"] = now_monotonic
        record["approved_expires_at"] = now_wall + APPROVED_TTL_SECONDS
        record["approved_expires_monotonic"] = (
            now_monotonic + APPROVED_TTL_SECONDS
        )
        _write_state(root, path, state_value)
        return True


def _handle_pretool(platform: str, request: Dict[str, object]) -> None:
    if request.get("hook_event_name") != "PreToolUse" or request.get("tool_name") != "Bash":
        return
    tool_input = request.get("tool_input")
    if not isinstance(tool_input, dict) or not isinstance(tool_input.get("command"), str):
        return
    command = tool_input["command"]
    try:
        analysis = analyze(command)
    except Exception:
        analysis = Analysis(matched=_raw_candidate(command), canonical=False)
    if not analysis.matched:
        return
    if platform == "claude":
        _decision("ask", "Recursive forced deletion requires your explicit approval.")
        return
    if not analysis.canonical:
        _decision(
            "deny",
            "Recursive forced rm is blocked. Reissue it as one direct rm command with only static absolute target paths, then request approval.",
        )
        return
    session_id = request.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        _decision("deny", "Recursive forced rm is blocked because the approval session is unavailable.")
        return
    try:
        released, token = _pretool_state(session_id, command)
    except GuardError as exc:
        _decision("deny", f"Recursive forced rm is blocked because the approval guard failed safely: {exc}.")
        return
    except Exception:
        _decision("deny", "Recursive forced rm is blocked because the approval guard failed safely.")
        return
    if released:
        return
    _decision(
        "deny",
        "Recursive forced rm is blocked pending Jake's approval. Show Jake the exact command and ask them to reply exactly: "
        f"approve rm-rf {token}",
    )


def _handle_user_prompt(request: Dict[str, object]) -> None:
    if request.get("hook_event_name") != "UserPromptSubmit":
        return
    prompt = request.get("prompt")
    session_id = request.get("session_id")
    if not isinstance(prompt, str) or not isinstance(session_id, str) or not session_id:
        return
    match = APPROVAL.fullmatch(prompt.strip())
    if not match:
        return
    try:
        approved = _approve_token(session_id, match.group(1))
    except GuardError as exc:
        _json_output({"systemMessage": f"rm-rf approval was not recorded: {exc}."})
        return
    except Exception:
        _json_output({"systemMessage": "rm-rf approval was not recorded because the guard failed safely."})
        return
    if approved:
        _json_output(
            {
                "hookSpecificOutput": {
                    "additionalContext": "One-time rm-rf approval recorded. Retry the exact absolute-target command once within two minutes.",
                    "hookEventName": "UserPromptSubmit",
                }
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("claude", "codex"), required=True)
    arguments = parser.parse_args()
    try:
        request = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeError):
        return
    if not isinstance(request, dict):
        return
    if arguments.platform == "codex" and request.get("hook_event_name") == "UserPromptSubmit":
        _handle_user_prompt(request)
    else:
        _handle_pretool(arguments.platform, request)


if __name__ == "__main__":
    main()
