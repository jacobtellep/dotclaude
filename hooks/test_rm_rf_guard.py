import concurrent.futures
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

if __package__:
    from . import rm_rf_guard
else:
    import rm_rf_guard


GUARD = Path(__file__).with_name("rm_rf_guard.py")
TOKEN_PHRASE = re.compile(r"approve rm-rf ([0-9a-f]{32})")


class RmRfGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        self.cwd = self.root / "unrelated" / "working-directory"
        self.cwd.mkdir(parents=True)
        self.env = os.environ.copy()
        self.env["CODEX_HOME"] = str(self.codex_home)

    def tearDown(self):
        self.temp.cleanup()

    def run_hook(self, platform, request):
        return self.run_raw_hook(platform, json.dumps(request))

    def run_raw_hook(self, platform, hook_input):
        result = subprocess.run(
            [sys.executable, str(GUARD), "--platform", platform],
            cwd=self.cwd,
            env=self.env,
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"guard exited {result.returncode}\nstdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        return result

    def pre_tool_use(self, platform, command, session_id="session-a"):
        return self.run_hook(
            platform,
            {
                "session_id": session_id,
                "cwd": str(self.cwd),
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": command},
            },
        )

    def user_prompt(self, prompt, session_id="session-a"):
        return self.run_hook(
            "codex",
            {
                "session_id": session_id,
                "cwd": str(self.cwd),
                "hook_event_name": "UserPromptSubmit",
                "prompt": prompt,
            },
        )

    def output(self, result):
        self.assertTrue(result.stdout, "expected a hook decision on stdout")
        return json.loads(result.stdout)

    def decision(self, result):
        payload = self.output(result)
        self.assertEqual(set(payload), {"hookSpecificOutput"})
        return payload["hookSpecificOutput"]

    def assert_ask(self, command):
        decision = self.decision(self.pre_tool_use("claude", command))
        self.assertEqual(decision["hookEventName"], "PreToolUse")
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertTrue(decision["permissionDecisionReason"])

    def assert_deny(self, result):
        decision = self.decision(result)
        self.assertEqual(decision["hookEventName"], "PreToolUse")
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertTrue(decision["permissionDecisionReason"])
        return decision["permissionDecisionReason"]

    def token_phrase(self, result):
        reason = self.assert_deny(result)
        match = TOKEN_PHRASE.search(reason)
        self.assertIsNotNone(match, reason)
        return match.group(0)

    def assert_no_approval_context(self, result):
        if not result.stdout:
            return
        payload = json.loads(result.stdout)
        context = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("retry the exact command", context.lower())

    def state_file_containing(self, text):
        state_root = self.codex_home / "rm-rf-guard"
        for path in state_root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                if text in path.read_text(encoding="utf-8"):
                    return path
            except (OSError, UnicodeDecodeError):
                continue
        self.fail(f"no state file contains {text!r}")

    def expire_token(self, phrase):
        state_file, state, record = self.state_record(phrase)
        status = record["status"]
        now_wall = time.time()
        now_monotonic = time.clock_gettime(time.CLOCK_MONOTONIC)
        shift = max(
            record[f"{status}_expires_at"] - now_wall,
            record[f"{status}_expires_monotonic"] - now_monotonic,
            0,
        ) + 1
        timestamp_fields = [
            key
            for key in record
            if key.endswith("_at") or key.endswith("_monotonic")
        ]
        self.assertTrue(timestamp_fields)
        for field in timestamp_fields:
            record[field] -= shift
        state_file.write_text(json.dumps(state), encoding="utf-8")

    def state_record(self, phrase):
        token = phrase.rsplit(" ", 1)[1]
        state_file = self.state_file_containing(token)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        matching = [
            record
            for record in state.get("records", {}).values()
            if record.get("token") == token
        ]
        self.assertEqual(len(matching), 1)
        return state_file, state, matching[0]

    def approval_records(self):
        state_root = self.codex_home / "rm-rf-guard"
        if not state_root.exists():
            return []
        records = []
        for state_file in state_root.glob("*.json"):
            state = json.loads(state_file.read_text(encoding="utf-8"))
            records.extend(state.get("records", {}).values())
        return records

    def assert_guard_error(self, result):
        reason = self.assert_deny(result)
        self.assertIsNone(TOKEN_PHRASE.search(reason), reason)
        self.assertRegex(reason.lower(), r"guard|state|safe|corrupt|failed")
        return reason

    def test_detects_every_bounded_recursive_force_form(self):
        commands = (
            "rm -rf /tmp/guard-target",
            "rm -fr /tmp/guard-target",
            "rm -r -f /tmp/guard-target",
            "rm -R -f /tmp/guard-target",
            "rm --recursive --force /tmp/guard-target",
            "rm -Rfv /tmp/guard-target",
            "rm -r$((1))f /tmp/guard-target",
            "/bin/rm -rf /tmp/guard-target",
            "/usr/bin/rm -fr /tmp/guard-target",
            "TARGET=/tmp/guard-target rm -rf /tmp/guard-target",
            "PATH+=:/private/tmp rm -rf /tmp/guard-target",
            "A[1]=x rm -rf /tmp/guard-target",
            "env TARGET=/tmp/guard-target rm -rf /tmp/guard-target",
            "command rm -rf /tmp/guard-target",
            "sudo -n rm -rf /tmp/guard-target",
            "printf '/tmp/guard-target\\n' | xargs rm -rf",
            "find /tmp/guard-target -type d -exec rm -rf {} +",
            "find /tmp/guard-target \\( -type d -exec rm -rf {} + \\)",
            "sh -c 'rm -rf /tmp/guard-target'",
            "bash -c \"rm -rf /tmp/guard-target\"",
            "zsh -c 'rm -rf /tmp/guard-target'",
            "true; rm -rf /tmp/guard-target",
            "true && rm -rf /tmp/guard-target",
            "false || rm -rf /tmp/guard-target",
            "printf x | rm -rf /tmp/guard-target",
            ">/dev/null rm -rf /tmp/guard-target",
            ">|/dev/null rm -rf /tmp/guard-target",
            "2>/dev/null rm -rf /tmp/guard-target",
            "rm 2>/dev/null -rf /tmp/guard-target",
            "rm -rf /tmp/guard-target >/dev/null",
            "true &&>/dev/null rm -rf /tmp/guard-target",
            "true |>/dev/null rm -rf /tmp/guard-target",
            "true\nrm -rf /tmp/guard-target",
            "echo value#tag; rm -rf /tmp/guard-target",
            "echo value\\\n#tag; rm -rf /tmp/guard-target",
            "TARGET=value#tag rm -rf /tmp/guard-target",
            "true # inert rm -rf /tmp/ignored\nrm -rf /tmp/guard-target",
            "(rm -rf /tmp/guard-target)",
            "echo $(rm -rf /tmp/guard-target)",
            "echo \"$(rm -rf /tmp/guard-target)\"",
            "echo `rm -rf /tmp/guard-target`",
            "echo \"`rm -rf /tmp/guard-target`\"",
            "echo $(( $(rm -rf /tmp/guard-target) ))",
            "echo $(( `rm -rf /tmp/guard-target` ))",
            "echo $(( ${x:-$(rm -rf /tmp/guard-target)} + 1 ))",
            "echo $(( $\\\n(rm -rf /tmp/guard-target) ))",
            "( ( echo $(( $(echo 1 # ((\n) + 1 )); rm -rf /tmp/guard-target ) )",
            "( x=1; echo $(( ${x:-(} + 1 )); rm -rf /tmp/guard-target )",
            "( ( x=1; echo \"$(( ${x:-'} + 1 ))\"; r\"\"m -r\"\"f /tmp/guard-target; # '\n{ :; } ) )",
            "echo \"$(echo ${x:-foo}; r\"\"m -r\"\"f /tmp/guard-target)\"",
            "echo \"$(echo ${x:-foo}; r\"m\" -r\"f\" /tmp/guard-target)\"",
            "echo \"$(echo ${x:-foo}; r'm' -r'f' /tmp/guard-target)\"",
            '"rm" -rf /tmp/guard-target "$(echo ${x:-"foo"})"',
            'rm "-rf" /tmp/guard-target "$(echo ${x:-"foo"})"',
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_ask(command)

    def test_detects_deeply_nested_command_substitutions(self):
        command = "rm -rf /tmp/guard-target"
        for _ in range(17):
            command = f"echo $(( $({command}) ))"
        self.assert_ask(command)

        inert = "echo rm -rf"
        for _ in range(17):
            inert = f"echo $(( $({inert}) ))"
        self.assertFalse(rm_rf_guard.analyze(inert).matched)

        bounded = "rm -rf /tmp/guard-target"
        for _ in range(rm_rf_guard.MAX_SUBSTITUTION_DEPTH + 1):
            bounded = f"echo $(( $({bounded}) ))"
        self.assertTrue(rm_rf_guard.analyze(bounded).matched)

    def test_claude_detects_env_path_options_with_values(self):
        commands = (
            "env -P /usr/bin rm -rf /tmp/guard-target",
            "env -P/usr/bin rm -rf /tmp/guard-target",
            "env -ivP /usr/bin rm -rf /tmp/guard-target",
            "env -ivP/usr/bin rm -rf /tmp/guard-target",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_ask(command)

    def test_claude_detects_env_split_string_forms(self):
        commands = (
            "env -S 'rm -rf /tmp/guard-target'",
            "env '-Srm -rf /tmp/guard-target'",
            "env --split-string 'rm -rf /tmp/guard-target'",
            "env --split-string='rm -rf /tmp/guard-target'",
            "env -iS 'rm -rf /tmp/guard-target'",
            "env '-iSrm -rf /tmp/guard-target'",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_ask(command)

    def test_claude_detects_sudo_timeout_options_with_values(self):
        commands = (
            "sudo -T 30 rm -rf /tmp/guard-target",
            "sudo -T30 rm -rf /tmp/guard-target",
            "sudo --command-timeout 30 rm -rf /tmp/guard-target",
            "sudo --command-timeout=30 rm -rf /tmp/guard-target",
            "sudo -nT 30 rm -rf /tmp/guard-target",
            "sudo -nT30 rm -rf /tmp/guard-target",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_ask(command)

    def test_claude_detects_xargs_bsd_options_with_values(self):
        commands = (
            "printf '/tmp/guard-target\\n' | xargs -J target rm -rf target",
            "printf '/tmp/guard-target\\n' | xargs -Jtarget rm -rf target",
            "printf '/tmp/guard-target\\n' | xargs -R 1 rm -rf",
            "printf '/tmp/guard-target\\n' | xargs -R1 rm -rf",
            "printf '/tmp/guard-target\\n' | xargs -S 1024 rm -rf",
            "printf '/tmp/guard-target\\n' | xargs -S1024 rm -rf",
            "printf '/tmp/guard-target\\n' | xargs -0P 2 rm -rf",
            "printf '/tmp/guard-target\\n' | xargs --max-procs 2 rm -rf",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_ask(command)

    def test_claude_detects_shell_c_after_long_options(self):
        commands = (
            "bash --norc -c 'rm -rf /tmp/guard-target'",
            "bash --rcfile /tmp/bashrc -c 'rm -rf /tmp/guard-target'",
            "zsh --no-rcs -c 'rm -rf /tmp/guard-target'",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assert_ask(command)

    def test_ignores_nonmatching_and_inert_rm_text(self):
        commands = (
            "rm /tmp/guard-target",
            "rm -r /tmp/guard-target",
            "rm -f /tmp/guard-target",
            "rm ./-rf",
            "rm -- -rf",
            "rm -r -- -f",
            "rm -f -- -r",
            "# rm -rf /tmp/guard-target",
            "# comment; rm -rf /tmp/guard-target",
            "true # rm -rf /tmp/guard-target",
            "true # comment; rm -rf /tmp/guard-target",
            "\\\n# comment; rm -rf /tmp/guard-target",
            "echo \\; rm -rf /tmp/guard-target",
            "echo ';' rm -rf /tmp/guard-target",
            "bash -- -c 'rm -rf /tmp/guard-target'",
            "bash /dev/null -c 'rm -rf /tmp/guard-target'",
            "bash --rcfile -c 'rm -rf /tmp/guard-target'",
            "echo hi > rm -rf /tmp/guard-target",
            "true >|/dev/null rm -rf /tmp/guard-target",
            "echo 'rm -rf /tmp/guard-target'",
            "echo '$(rm -rf /tmp/guard-target)'",
            "echo '`rm -rf /tmp/guard-target`'",
            "echo '$\\\n(rm -rf /tmp/guard-target)'",
            'echo "$(\'r\\\nm\' -rf /tmp/guard-target)"',
            "echo \"$(echo ${HOME})\"",
            'rm -- -rf "$(echo ${x:-"foo"})"',
            'echo rm -rf "$(echo ${x:-"foo"})"',
            "printf '%s\\n' 'rm -rf /tmp/guard-target'",
        )
        for platform in ("claude", "codex"):
            for command in commands:
                with self.subTest(platform=platform, command=command):
                    result = self.pre_tool_use(platform, command)
                    self.assertEqual(result.stdout, "")

    def test_ignores_rm_subtraction_in_arithmetic_contexts(self):
        commands = (
            "rm=7 rf=2; echo $((rm -rf))",
            "rm=7 rf=2; echo $(( rm -rf ))",
            "rm=7 rf=2; echo \"$((rm -rf))\"",
            "rm=7 rf=2; value=$(( rm -rf )); echo \"$value\"",
            "rm=7 rf=2; (( rm -rf ))",
            "rm=7 rf=2; echo $(( rm \\\n- rf ))",
            "rm=7 rf=2; echo $\\\n(( rm -rf ))",
            "rm=7 rf=2 x=1; echo $(( rm -rf + ${x} ))",
            "rm=7 rf=2 x=1; (( rm -rf + ${x} ))",
            "rm=7 rf=2 x=1 y=1; echo $(( rm -rf + ${x:-$y} ))",
            'rm=7 rf=2; echo $(( rm -rf + ${x:-"1"} ))',
            "rm=7 rf=2; echo $(( rm -rf + ${x:-$(echo 1)} ))",
            'rm=7 rf=2; echo $(( rm -rf + ${x:-"$(echo 1)"} ))',
            "rm=7 rf=2; echo $(( rm -rf + ${x:-$((1))} ))",
            "echo \"$(echo ${x:-$y})\"",
        )
        for platform in ("claude", "codex"):
            for command in commands:
                with self.subTest(platform=platform, command=command):
                    result = self.pre_tool_use(platform, command)
                    self.assertEqual(result.stdout, "")

    def test_large_inert_command_does_not_switch_to_context_free_matching(self):
        command = 'echo rm -rf "$(echo ${x:-"foo"})"' + (" x" * 25_000)
        self.assertFalse(rm_rf_guard.analyze(command).matched)

    def test_parser_error_fails_closed_only_for_a_plausible_candidate(self):
        destructive = self.pre_tool_use(
            "claude", "rm -rf /tmp/guard-target 'unterminated"
        )
        self.assertEqual(
            self.decision(destructive)["permissionDecision"],
            "ask",
        )

        unrelated = self.pre_tool_use("claude", "echo 'unterminated")
        self.assertEqual(unrelated.stdout, "")

        continued_quoted_text = self.pre_tool_use(
            "claude", 'echo "r\\\nm -rf /tmp/guard-target" \'unterminated'
        )
        self.assertEqual(continued_quoted_text.stdout, "")

    def test_codex_parser_error_fails_closed_only_for_a_plausible_candidate(self):
        destructive = self.pre_tool_use(
            "codex", "rm -rf /tmp/guard-target 'unterminated"
        )
        reason = self.assert_deny(destructive)
        self.assertIsNone(TOKEN_PHRASE.search(reason), reason)

        unrelated = self.pre_tool_use("codex", "echo 'unterminated")
        self.assertEqual(unrelated.stdout, "")

    def test_malformed_or_unrelated_codex_hook_input_is_nonblocking(self):
        malformed = self.run_raw_hook("codex", "{not json")
        self.assertEqual(malformed.stdout, "")
        self.assertEqual(malformed.stderr, "")

        wrong_tool = self.run_hook(
            "codex",
            {
                "session_id": "session-a",
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"command": "rm -rf /tmp/guard-target"},
            },
        )
        self.assertEqual(wrong_tool.stdout, "")

        malformed_request = self.run_hook("codex", ["not", "an", "object"])
        self.assertEqual(malformed_request.stdout, "")

    def test_claude_match_emits_exact_native_ask_shape(self):
        result = self.pre_tool_use("claude", "rm -rf /tmp/guard-target")
        self.assertFalse(result.stderr)
        decision = self.decision(result)
        self.assertEqual(
            set(decision),
            {
                "hookEventName",
                "permissionDecision",
                "permissionDecisionReason",
            },
        )
        self.assertEqual(decision["hookEventName"], "PreToolUse")
        self.assertEqual(decision["permissionDecision"], "ask")
        self.assertTrue(decision["permissionDecisionReason"].strip())

    def test_codex_noncanonical_matches_deny_without_issuing_a_token(self):
        commands = (
            "rm -rf relative-target",
            "rm -rf $HOME/guard-target",
            "rm -rf ~/guard-target",
            "rm -rf /tmp/guard-*",
            "rm -rf /tmp/$((1))",
            "rm -rf /tmp/x$((1))y",
            "rm -r$((1))f /tmp/guard-target",
            "rm -rf $(printf /tmp/guard-target)",
            "TARGET=/tmp/guard-target rm -rf /tmp/guard-target",
            "env TARGET=/tmp/guard-target rm -rf /tmp/guard-target",
            "command rm -rf /tmp/guard-target",
            "sudo rm -rf /tmp/guard-target",
            "printf '/tmp/guard-target\\n' | xargs rm -rf",
            "find /tmp/guard-target -exec rm -rf {} +",
            "sh -c 'rm -rf /tmp/guard-target'",
            "rm -rf /tmp/guard-target && true",
            "true || rm -rf /tmp/guard-target",
            "true\nrm -rf /tmp/guard-target",
            "(rm -rf /tmp/guard-target)",
            "echo `rm -rf /tmp/guard-target`",
            "rm -rf /tmp/guard-target; rm -rf /tmp/other-target",
            "rm -rf /tmp/guard-target > /tmp/guard-log",
            ">/dev/null rm -rf /tmp/guard-target",
            "rm 2>/dev/null -rf /tmp/guard-target",
            "rm -rf",
        )
        for command in commands:
            with self.subTest(command=command):
                reason = self.assert_deny(self.pre_tool_use("codex", command))
                self.assertIsNone(TOKEN_PHRASE.search(reason), reason)
                self.assertIn("direct", reason.lower())
                self.assertIn("absolute", reason.lower())
        self.assertEqual(self.approval_records(), [])

    def test_codex_issues_tokens_for_all_canonical_spellings(self):
        commands = (
            "rm -rf /tmp/guard-target",
            "rm -fr /tmp/guard-target",
            "rm -r -f /tmp/guard-target",
            "rm -R -f /tmp/guard-target",
            "rm --recursive --force /tmp/guard-target",
            "rm -Rfv /tmp/guard-target",
            "/bin/rm -rf /tmp/guard-target",
            "/usr/bin/rm -fr /tmp/guard-target",
            "rm -rf -- /tmp/guard-target",
            "rm -rf /tmp/guard-target /var/tmp/other-target",
            "rm -rf '/tmp/guard target'",
            "rm -rf /tmp/guard-target#suffix",
        )
        for command in commands:
            with self.subTest(command=command):
                self.token_phrase(self.pre_tool_use("codex", command))

    def test_first_canonical_attempt_reuses_one_pending_token(self):
        command = "rm -rf /tmp/guard-target"
        first = self.token_phrase(self.pre_tool_use("codex", command))
        _, _, pending = self.state_record(first)
        self.assertAlmostEqual(
            pending["pending_expires_at"] - pending["created_at"],
            10 * 60,
            delta=1,
        )
        repeated = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertEqual(repeated, first)

    def test_same_session_exact_phrase_releases_once_then_denies_again(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))

        approval = self.user_prompt(phrase)
        context = self.decision(approval)
        self.assertEqual(context["hookEventName"], "UserPromptSubmit")
        self.assertIn("retry", context["additionalContext"].lower())
        _, _, approved = self.state_record(phrase)
        self.assertAlmostEqual(
            approved["approved_expires_at"] - approved["approved_at"],
            2 * 60,
            delta=1,
        )

        released = self.pre_tool_use("codex", command)
        self.assertEqual(released.stdout, "")

        denied_again = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(denied_again, phrase)

    def test_approval_is_bound_to_same_session(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(
            self.pre_tool_use("codex", command, session_id="session-a")
        )
        wrong_session = self.user_prompt(phrase, session_id="session-b")
        self.assert_no_approval_context(wrong_session)

        retry = self.pre_tool_use("codex", command, session_id="session-a")
        self.assertEqual(self.token_phrase(retry), phrase)

    def test_approval_is_bound_to_exact_command(self):
        command = "rm -rf /tmp/guard-target"
        changed = "rm -rf /tmp/other-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.user_prompt(phrase)

        changed_phrase = self.token_phrase(self.pre_tool_use("codex", changed))
        self.assertNotEqual(changed_phrase, phrase)
        original_retry = self.pre_tool_use("codex", command)
        self.assertEqual(original_retry.stdout, "")

    def test_extra_prose_or_changed_case_does_not_approve(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))

        extra_prose = self.user_prompt(f"please {phrase}")
        self.assert_no_approval_context(extra_prose)
        changed_case = self.user_prompt(phrase.upper())
        self.assert_no_approval_context(changed_case)

        retry = self.pre_tool_use("codex", command)
        self.assertEqual(self.token_phrase(retry), phrase)

    def test_unknown_token_does_not_approve_but_surrounding_whitespace_is_trimmed(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))

        unknown = self.user_prompt("approve rm-rf " + "0" * 32)
        self.assert_no_approval_context(unknown)
        self.assertEqual(
            self.token_phrase(self.pre_tool_use("codex", command)),
            phrase,
        )

        approval = self.user_prompt(f"  {phrase}\n")
        context = self.decision(approval)["additionalContext"]
        self.assertIn("retry", context.lower())
        self.assertEqual(self.pre_tool_use("codex", command).stdout, "")

    def test_expired_pending_token_cannot_be_approved(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.expire_token(phrase)

        approval = self.user_prompt(phrase)
        self.assert_no_approval_context(approval)
        replacement = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(replacement, phrase)
        state_file = self.state_file_containing(replacement.rsplit(" ", 1)[1])
        self.assertNotIn(
            phrase.rsplit(" ", 1)[1],
            state_file.read_text(encoding="utf-8"),
        )

    def test_expired_approval_does_not_release_the_guard(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.user_prompt(phrase)
        self.expire_token(phrase)

        replacement = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(replacement, phrase)

    def test_monotonic_deadline_expires_pending_token(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        state_file, state, record = self.state_record(phrase)
        self.assertGreater(record["pending_expires_at"], time.time())
        record["pending_expires_monotonic"] = record["created_monotonic"] + 1e-6
        state_file.write_text(json.dumps(state), encoding="utf-8")

        approval = self.user_prompt(phrase)
        self.assert_no_approval_context(approval)
        replacement = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(replacement, phrase)

    def test_monotonic_deadline_expires_approved_token(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.user_prompt(phrase)
        state_file, state, record = self.state_record(phrase)
        self.assertGreater(record["approved_expires_at"], time.time())
        record["approved_expires_monotonic"] = (
            record["approved_monotonic"] + 1e-6
        )
        state_file.write_text(json.dumps(state), encoding="utf-8")

        replacement = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(replacement, phrase)

    def test_clock_offset_drift_expires_approved_token(self):
        command = "rm -rf /tmp/guard-target"
        for offset_delta in (-60, 60):
            session_id = f"session-offset-{offset_delta}"
            with self.subTest(offset_delta=offset_delta):
                phrase = self.token_phrase(
                    self.pre_tool_use("codex", command, session_id=session_id)
                )
                self.user_prompt(phrase, session_id=session_id)
                state_file, state, record = self.state_record(phrase)
                record["clock_offset"] += offset_delta
                for field in record:
                    if field.endswith("_at"):
                        record[field] += offset_delta
                self.assertGreater(record["approved_expires_at"], time.time())
                state_file.write_text(json.dumps(state), encoding="utf-8")

                replacement = self.token_phrase(
                    self.pre_tool_use("codex", command, session_id=session_id)
                )
                self.assertNotEqual(replacement, phrase)

    def test_monotonic_clock_rollback_expires_approved_token(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.user_prompt(phrase)
        state_file, state, record = self.state_record(phrase)
        for field in record:
            if field.endswith("_at") or field.endswith("_monotonic"):
                record[field] += 60
        self.assertGreater(
            record["created_monotonic"],
            time.clock_gettime(time.CLOCK_MONOTONIC),
        )
        state_file.write_text(json.dumps(state), encoding="utf-8")

        replacement = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(replacement, phrase)

    def test_future_approved_timestamps_do_not_release_the_guard(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.user_prompt(phrase)
        state_file, state, record = self.state_record(phrase)
        for field in (
            "approved_at",
            "approved_monotonic",
            "approved_expires_at",
            "approved_expires_monotonic",
        ):
            record[field] += 60
        state_file.write_text(json.dumps(state), encoding="utf-8")

        replacement = self.token_phrase(self.pre_tool_use("codex", command))
        self.assertNotEqual(replacement, phrase)

    def test_parseable_corrupt_approved_records_fail_closed(self):
        mutations = {
            "command hash mismatch": lambda record: record.update(
                command_hash="0" * 64
            ),
            "missing approved field": lambda record: record.pop(
                "approved_expires_at"
            ),
            "nonfinite deadline": lambda record: record.update(
                approved_expires_at=float("inf")
            ),
            "extra field": lambda record: record.update(unexpected=True),
        }
        command = "rm -rf /tmp/guard-target"
        for case, mutate in mutations.items():
            session_id = f"session-corrupt-{case}"
            with self.subTest(case=case):
                phrase = self.token_phrase(
                    self.pre_tool_use("codex", command, session_id=session_id)
                )
                self.user_prompt(phrase, session_id=session_id)
                state_file, state, record = self.state_record(phrase)
                self.assertEqual(record["status"], "approved")
                mutate(record)
                state_file.write_text(json.dumps(state), encoding="utf-8")

                self.assert_guard_error(
                    self.pre_tool_use("codex", command, session_id=session_id)
                )

    def test_corrupt_state_does_not_release_the_guard(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        state_file = self.state_file_containing(phrase.rsplit(" ", 1)[1])
        state_file.write_text("{not valid json", encoding="utf-8")

        approval = self.user_prompt(phrase)
        self.assert_no_approval_context(approval)
        warning = f"{approval.stdout}\n{approval.stderr}".lower()
        self.assertRegex(warning, r"warn|corrupt|guard|state")
        self.assert_guard_error(self.pre_tool_use("codex", command))

    def test_symlinked_state_root_fails_closed(self):
        state_root = self.codex_home / "rm-rf-guard"
        symlink_target = self.root / "unsafe-state-target"
        symlink_target.mkdir()
        state_root.symlink_to(symlink_target, target_is_directory=True)

        reason = self.assert_deny(
            self.pre_tool_use("codex", "rm -rf /tmp/guard-target")
        )
        self.assertIsNone(TOKEN_PHRASE.search(reason), reason)
        self.assertRegex(reason.lower(), r"guard|state|safe|symlink")

    def test_symlinked_session_state_does_not_release_the_guard(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        token = phrase.rsplit(" ", 1)[1]
        state_file = self.state_file_containing(token)
        external = self.root / "external-state.json"
        external.write_bytes(state_file.read_bytes())
        state_file.unlink()
        state_file.symlink_to(external)

        approval = self.user_prompt(phrase)
        self.assert_no_approval_context(approval)
        self.assert_guard_error(self.pre_tool_use("codex", command))

    def test_nonregular_session_state_does_not_release_the_guard(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        state_file = self.state_file_containing(phrase.rsplit(" ", 1)[1])
        state_file.unlink()
        state_file.mkdir()

        approval = self.user_prompt(phrase)
        self.assert_no_approval_context(approval)
        self.assert_guard_error(self.pre_tool_use("codex", command))

    def test_busy_session_lock_fails_closed_before_host_timeout(self):
        command = "rm -rf /tmp/guard-target"
        self.token_phrase(self.pre_tool_use("codex", command))
        lock_path = next((self.codex_home / "rm-rf-guard").glob("*.lock"))
        with lock_path.open("r+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            started = time.clock_gettime(time.CLOCK_MONOTONIC)
            result = self.pre_tool_use("codex", command)
            elapsed = time.clock_gettime(time.CLOCK_MONOTONIC) - started
        self.assertLess(elapsed, 4)
        self.assert_guard_error(result)

    def run_concurrently(self, count, callback):
        barrier = threading.Barrier(count)

        def invoke(index):
            barrier.wait(timeout=5)
            return callback(index)

        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(invoke, index) for index in range(count)]
            return [future.result(timeout=15) for future in futures]

    def test_concurrent_first_attempts_reuse_one_token(self):
        command = "rm -rf /tmp/guard-target"
        results = self.run_concurrently(
            8,
            lambda _: self.pre_tool_use("codex", command),
        )
        phrases = {self.token_phrase(result) for result in results}
        self.assertEqual(len(phrases), 1)
        token = phrases.pop().rsplit(" ", 1)[1]
        state_file = self.state_file_containing(token)
        state = json.loads(state_file.read_text(encoding="utf-8"))
        matching = [
            record
            for record in state.get("records", {}).values()
            if record.get("token") == token and record.get("status") == "pending"
        ]
        self.assertEqual(len(matching), 1)

    def test_concurrent_approved_retries_release_exactly_one_process(self):
        command = "rm -rf /tmp/guard-target"
        phrase = self.token_phrase(self.pre_tool_use("codex", command))
        self.user_prompt(phrase)

        results = self.run_concurrently(
            8,
            lambda _: self.pre_tool_use("codex", command),
        )
        released = [result for result in results if result.stdout == ""]
        denied = [result for result in results if result.stdout != ""]
        self.assertEqual(len(released), 1)
        self.assertEqual(len(denied), 7)
        for result in denied:
            self.assert_deny(result)


if __name__ == "__main__":
    unittest.main()
