import re

from swebench.harness.constants import TestStatus


def parse_log_cargo(log: str) -> dict[str, str]:
    """
    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    pattern = r"^test\s+(\S+)\s+\.\.\.\s+(\w+)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            test_name, outcome = match.groups()
            if outcome == "ok":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif outcome == "FAILED":
                test_status_map[test_name] = TestStatus.FAILED.value

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