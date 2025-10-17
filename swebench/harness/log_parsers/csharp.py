import re
from swebench.harness.constants import TestStatus
from swebench.harness.test_spec.test_spec import TestSpec


def parse_log_dotnet(log: str, test_spec: TestSpec) -> dict[str, str]:
    """
    Parser for .NET test logs (supports xUnit, NUnit, MSTest, and general frameworks).
got    Looks for summary lines and maps test results. Handles more edge cases and logs.
    """
    test_status_map = {}

    nunit_pattern = r"Passed:\s*(\d+),\s*Failed:\s*(\d+),\s*Skipped:\s*(\d+)"
    nunit_match = re.search(nunit_pattern, log)
    if nunit_match:
        passed, failed, skipped = map(int, nunit_match.groups())
        for i in range(passed):
            test_status_map[f"nunit_passed_{i}"] = TestStatus.PASSED.value
        for i in range(failed):
            test_status_map[f"nunit_failed_{i}"] = TestStatus.FAILED.value
        for i in range(skipped):
            test_status_map[f"nunit_skipped_{i}"] = TestStatus.SKIPPED.value
        return test_status_map

    xunit_pattern = r"Total tests:\s*\d+.*?Passed:\s*(\d+).*?Failed:\s*(\d+).*?Skipped:\s*(\d+)"
    xunit_match = re.search(xunit_pattern, log, re.DOTALL)
    if xunit_match:
        passed, failed, skipped = map(int, xunit_match.groups())
        for i in range(passed):
            test_status_map[f"xunit_passed_{i}"] = TestStatus.PASSED.value
        for i in range(failed):
            test_status_map[f"xunit_failed_{i}"] = TestStatus.FAILED.value
        for i in range(skipped):
            test_status_map[f"xunit_skipped_{i}"] = TestStatus.SKIPPED.value
        return test_status_map

    mstest_pattern = r"Total tests:\s*(\d+).*?Passed:\s*(\d+).*?Failed:\s*(\d+).*?Skipped:\s*(\d+)"
    mstest_match = re.search(mstest_pattern, log, re.DOTALL)
    if mstest_match:
        total, passed, failed, skipped = map(int, mstest_match.groups())
        for i in range(passed):
            test_status_map[f"mstest_passed_{i}"] = TestStatus.PASSED.value
        for i in range(failed):
            test_status_map[f"mstest_failed_{i}"] = TestStatus.FAILED.value
        for i in range(skipped):
            test_status_map[f"mstest_skipped_{i}"] = TestStatus.SKIPPED.value
        return test_status_map

    for line in log.splitlines():
        if "Passed" in line:
            test_status_map[line.strip()] = TestStatus.PASSED.value
        elif "Failed" in line:
            test_status_map[line.strip()] = TestStatus.FAILED.value
        elif "Skipped" in line:
            test_status_map[line.strip()] = TestStatus.SKIPPED.value

    if not test_status_map:
        test_status_map['warning'] = "No standard test result format found in log"
    return test_status_map

def get_cs_parser_by_name(name: str):
    if name == "dotnet":
        return parse_log_dotnet
    return parse_log_dotnet


MAP_REPO_TO_PARSER_CS = {
    "dotnet/runtime": parse_log_dotnet,
    "dotnet/aspnetcore": parse_log_dotnet,
    "dotnet/mstest": parse_log_dotnet,
}
