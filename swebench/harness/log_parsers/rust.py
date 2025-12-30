import re

from swebench.harness.constants import TestStatus


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    # Pattern matches ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def parse_log_cargo(log: str) -> dict[str, str]:
    """
    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    # Pattern 1: Standard format - test name and result on same line
    # Example: "test my::test ... ok"
    pattern_complete = r"^test\s+(\S+)\s+\.\.\.\s+(ok|FAILED)$"

    # Pattern 2: Test result embedded in other text (must have ok or FAILED)
    # Example: "some text test my::test ... ok more text"
    pattern_embedded = r"test\s+(\S+)\s+\.\.\.\s+(ok|FAILED)"

    # Pattern 3: Test name with ... but no result or invalid result (result comes later)
    # Example: "test my::test ... " or "test my::test ... thread panicked"
    pattern_incomplete = r"^test\s+(\S+)\s+\.\.\."

    # Pattern 4: Standalone result (ok/FAILED) on its own line
    pattern_result = r"^(ok|FAILED)$"

    # Pattern 5: Result at start of line followed by other text (no whitespace)
    # Example: "okLE Msb0: ..." where "ok" is concatenated with following text
    pattern_result_concatenated = r"^(ok|FAILED)(?=\S)"

    # Pattern 6: Result at start of line followed by whitespace and other text
    # Example: "        ok    Function {" where ok is surrounded by whitespace
    pattern_result_with_whitespace = r"^(ok|FAILED)\s+\S"

    # Pattern 7: Result at end of line (possibly concatenated with other text)
    # Example: "facet_reflect::wipok" or "Shape Macroedok" or "Vec<i32>ok"
    pattern_result_at_end = r"(ok|FAILED)$"

    # Track pending tests that haven't gotten a result yet
    pending_test = None

    for line in log.split("\n"):
        # Remove ANSI codes first, then strip whitespace
        line_stripped = strip_ansi_codes(line).strip()

        # First, try to match complete test lines (Pattern 1)
        match = re.match(pattern_complete, line_stripped)
        if match:
            test_name, outcome = match.groups()
            test_status_map[test_name] = TestStatus.PASSED.value if outcome == "ok" else TestStatus.FAILED.value
            pending_test = None
            continue

        # Try to match embedded test results (Pattern 2)
        match = re.search(pattern_embedded, line_stripped)
        if match:
            test_name, outcome = match.groups()
            test_status_map[test_name] = TestStatus.PASSED.value if outcome == "ok" else TestStatus.FAILED.value
            pending_test = None
            continue

        # Check for incomplete test lines (Pattern 3)
        # Only process if we don't already have a pending test
        if not pending_test:
            # Try to match from beginning of line first
            match = re.match(pattern_incomplete, line_stripped)
            if match:
                test_name = match.group(1)
                # Check if this line has a valid result after ...
                # If not, mark it as pending
                result_check = re.match(r"^test\s+\S+\s+\.\.\.\s+(ok|FAILED)", line_stripped)
                if not result_check:
                    pending_test = test_name
                continue

            # Also try to find test ... pattern anywhere in the line
            # (for cases where test appears after other text like TRACE logs)
            match = re.search(r"test\s+(\S+)\s+\.\.\.", line_stripped)
            if match:
                test_name = match.group(1)
                # Make sure there's no valid result (ok/FAILED) immediately after ... on this line
                result_check = re.search(r"test\s+\S+\s+\.\.\.\s+(ok|FAILED)", line_stripped)
                if not result_check:
                    pending_test = test_name
                continue

        # Check for results when we have a pending test
        if pending_test:
            # First try standalone result (Pattern 4)
            match = re.match(pattern_result, line_stripped)
            if match:
                outcome = match.group(1)
                test_status_map[pending_test] = TestStatus.PASSED.value if outcome == "ok" else TestStatus.FAILED.value
                pending_test = None
                continue

            # Then try concatenated result (Pattern 5)
            # This handles cases like "okLE Msb0:..." where ok is stuck to other text
            match = re.match(pattern_result_concatenated, line_stripped)
            if match:
                outcome = match.group(1)
                test_status_map[pending_test] = TestStatus.PASSED.value if outcome == "ok" else TestStatus.FAILED.value
                pending_test = None
                continue

            # Then try result with whitespace (Pattern 6)
            # This handles cases like "        ok    Function {" where ok has whitespace around it
            match = re.match(pattern_result_with_whitespace, line_stripped)
            if match:
                outcome = match.group(1)
                test_status_map[pending_test] = TestStatus.PASSED.value if outcome == "ok" else TestStatus.FAILED.value
                pending_test = None
                continue

            # Finally try result at end of line (Pattern 7)
            # This handles cases like "wipok" or "Macroedok" where ok is concatenated at the end
            match = re.search(pattern_result_at_end, line_stripped)
            if match:
                outcome = match.group(1)
                test_status_map[pending_test] = TestStatus.PASSED.value if outcome == "ok" else TestStatus.FAILED.value
                pending_test = None
                continue

    return test_status_map

def get_rust_parser_by_name(name: str):
    if name=="cargo":
        return parse_log_cargo
    return parse_log_cargo

MAP_REPO_TO_PARSER_RUST = {
    "BurntSushi/ripgrep": parse_log_cargo,
    "sharkdp/bat": parse_log_cargo,
    "astral-sh/ruff": parse_log_cargo,
    "tokio-rs/tokio": parse_log_cargo,
    "uutils/coreutils": parse_log_cargo,
    "nushell/nushell": parse_log_cargo,
    "tokio-rs/axum": parse_log_cargo,
}