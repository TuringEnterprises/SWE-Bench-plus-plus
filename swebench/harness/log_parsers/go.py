import re
from swebench.harness.constants import TestStatus


def parse_log_gotest(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with 'go test'

    Args:
        log (str): log content
        test_spec (TestSpec): test spec (unused)
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    # Pattern to match test result lines
    pattern = r"^--- (PASS|FAIL|SKIP): (.+) \((.+)\)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name, _duration = match.groups()
            if status == "PASS":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "FAIL":
                test_status_map[test_name] = TestStatus.FAILED.value
            elif status == "SKIP":
                test_status_map[test_name] = TestStatus.SKIPPED.value

    return test_status_map

def get_go_parser_by_name(name: str):
    if name=="gotest":
        return parse_log_gotest
    return parse_log_gotest

MAP_REPO_TO_PARSER_GO = {
    "caddyserver/caddy": parse_log_gotest,
    "hashicorp/terraform": parse_log_gotest,
    "prometheus/prometheus": parse_log_gotest,
    "gohugoio/hugo": parse_log_gotest,
    "gin-gonic/gin": parse_log_gotest,
    "kubernetes/kubernetes": parse_log_gotest,
}
