import re
import json

from swebench.harness.constants import TestStatus


def parse_log_minitest(log: str) -> dict[str, str]:
    """
    Parses Minitest logs from classic or verbose format.

    Args:
        log (str): log content
        test_spec (TestSpec): unused here, but part of interface

    Returns:
        dict[str, str]: test name to status ("passed"/"failed") map
    """
    test_status_map = {}

    # First format: SomeTest. ... = .
    # Second format: SomeTest#test_method = 0.00 s = F
    patterns = [
        re.compile(r"^(.+)\. .*=.*(\.|F|E).*$"),  # old
        re.compile(r"^(.*?#.*?) = [\d.]+ s = (\.|F|E)$"),  # new
    ]

    for line in log.split("\n"):
        line = line.strip()
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                test_name, outcome = match.groups()
                if outcome == ".":
                    test_status_map[test_name] = TestStatus.PASSED.value
                elif outcome in {"F", "E"}:
                    test_status_map[test_name] = TestStatus.FAILED.value
                break  # stop after first matching pattern

    return test_status_map


def parse_log_cucumber(log: str) -> dict[str, str]:
    """
    Parse Cucumber test execution report.
    """

    def parse_json_report(data):
        """
        Parse JSON report.
        """

        def _has_failed(items) -> bool:
            """
            Check if any of the given items has failed.
            """
            for item in items:
                status = item.get("result", {}).get("status", "").lower()
                if status and status == "failed":
                    return True
            return False

        # Test name to status map
        test_status_map = {}

        # Parse test results
        for feature in data:
            if not isinstance(feature, dict):
                continue
            feature_name = feature.get("name", "<feature>")
            last_background_failed = False
            for element in feature.get("elements", []):
                if not isinstance(element, dict):
                    continue
                element_type = element.get("type", "").lower()
                element_keyword = element.get("keyword", "").lower()

                if element_type == "background" or element_keyword == "background":
                    last_background_failed = _has_failed(element)
                    continue

                if element_type in {"scenario", "scenario_outline"} or element_keyword == "scenario":
                    scenario_name = element.get("name", "<scenario>")
                    test_name = f"{feature_name} > {scenario_name}"
                    if (
                        last_background_failed
                        or _has_failed(element.get("before", []))
                        or _has_failed(element.get("steps", []))
                        or _has_failed(element.get("after", []))
                    ):
                        test_status_map[test_name] = TestStatus.FAILED.value
                    else:
                        test_status_map[test_name] = TestStatus.PASSED.value

        return test_status_map

    # Detect Cucumber JSON
    json_match = re.search(r"\[\s*\{.*\}\s*\]", log, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
        except ValueError:
            pass
        else:
            try:
                return parse_json_report(data)
            except KeyError:
                pass

    return {}


def parse_log_ruby_unit(log: str) -> dict[str, str]:
    test_status_map = {}

    pattern = r"^\s*(?:test: )?(.+):\s+(\.|E\b|F\b|O\b)"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            test_name, outcome = match.groups()
            if outcome == ".":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif outcome in ["E", "F"]:
                test_status_map[test_name] = TestStatus.FAILED.value
            elif outcome == "O":
                test_status_map[test_name] = TestStatus.SKIPPED.value

    return test_status_map


def parse_log_rspec(log: str) -> dict[str, str]:
    """
    Parse RSpec test execution report.
    """

    def parse_json_report(data):
        """
        Parse JSON report.
        """
        # Test name to status map
        test_status_map = {}

        # Parse test results
        for item in data.get("examples", []):
            test_name = item["full_description"]
            status = item["status"]
            if status == "passed":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "failed":
                test_status_map[test_name] = TestStatus.FAILED.value

        return test_status_map

    # Detect RSpec JSON
    rspec_json_line = [line for line in log.split("\n") if '"examples":[{' in line]
    if rspec_json_line:
        json_pattern = r'\{.*"examples".*\}'
        json_match = re.search(json_pattern, rspec_json_line[0], re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                data = json.loads(json_str)
            except ValueError:
                pass
            else:
                try:
                    return parse_json_report(data)
                except KeyError:
                    pass

    return {}


def parse_log_tap(log: str) -> dict[str, str]:
    """
    Parser for TAP test execution report.
    """
    # Test name to status map
    test_status_map = {}

    # Regex to match test result reporting lines from the log and to extract test name and status
    pattern = re.compile(
        r"^\s*(?:\d+:\s*)*"
        r"(not[ \t]+ok|ok)\b"  # test status
        r"(?:\s+(\d+))?"  # optional test number
        r"\s+-\s+([^#\n]*?)"  # test name
        r"(?:\s*#\s*(SKIP|TODO)\b"  # optional directive
        r"(?:\s+(.*))?)?"  # optional reason
        r"\s*$",
        re.IGNORECASE,
    )

    # Split the log into multiple lines and extract the executed tests along with their statuses
    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, _, test_name, directive, _ = match.groups()
            test_name = test_name.strip()
            status = status.strip().lower()
            if directive:
                continue
            if status == "ok":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "not ok":
                test_status_map[test_name] = TestStatus.FAILED.value

    return test_status_map


def parse_log_jekyll(log: str) -> dict[str, str]:
    """
    Different jekyll instances use different test runners and log formats.
    This function selects the appropriate log parser based on the instance id.
    """
    pr_number = test_spec.instance_id.split("-")[1]

    if pr_number in ["9141", "8047", "8167"]:
        return parse_log_minitest(log, test_spec)
    elif pr_number in ["8761", "8771"]:
        return parse_log_cucumber(log, test_spec)
    else:
        raise ValueError(f"Unknown instance id: {test_spec.instance_id}")


def get_ruby_parser_by_name(name: str):
    if name == "rubyunit":
        return parse_log_ruby_unit
    if name == "minitest":
        return parse_log_minitest
    if name == "rspec":
        return parse_log_rspec
    if name == "cucumber":
        return parse_log_cucumber
    if name == "tap":
        return parse_log_tap
    return parse_log_ruby_unit


MAP_REPO_TO_PARSER_RUBY = {
    "jekyll/jekyll": parse_log_jekyll,
    "fluent/fluentd": parse_log_ruby_unit,
    "fastlane/fastlane": parse_log_rspec,
    "jordansissel/fpm": parse_log_rspec,
    "faker-ruby/faker": parse_log_ruby_unit,
    "rubocop/rubocop": parse_log_rspec,
}
