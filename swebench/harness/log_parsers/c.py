import re
import xml.etree.ElementTree as ET

from swebench.harness.constants import TestStatus


def parse_log_redis(log: str) -> dict[str, str]:
    """
    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    pattern = r"^\[(ok|err|skip|ignore)\]:\s(.+?)(?:\s\((\d+\s*m?s)\))?$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name, _duration = match.groups()
            if status == "ok":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "err":
                # Strip out file path information from failed test names
                test_name = re.sub(r"\s+in\s+\S+$", "", test_name)
                test_status_map[test_name] = TestStatus.FAILED.value
            elif status == "skip" or status == "ignore":
                test_status_map[test_name] = TestStatus.SKIPPED.value

    return test_status_map


def parse_log_jq(log: str) -> dict[str, str]:
    """
    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}

    pattern = r"^\s*(PASS|FAIL):\s(.+)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name = match.groups()
            if status == "PASS":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "FAIL":
                test_status_map[test_name] = TestStatus.FAILED.value
    return test_status_map


def parse_log_micropython_test(log: str) -> dict[str, str]:
    test_status_map = {}

    pattern = r"^(pass|FAIL|skip)\s+(.+)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name = match.groups()
            if status == "pass":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "FAIL":
                test_status_map[test_name] = TestStatus.FAILED.value
            elif status == "skip":
                test_status_map[test_name] = TestStatus.SKIPPED.value

    return test_status_map


def parse_log_googletest(log: str) -> dict[str, str]:
    test_status_map = {}

    pattern = r"^.*\[\s*(OK|FAILED)\s*\]\s(.*)\s\(.*\)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name = match.groups()
            if status == "OK":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "FAILED":
                test_status_map[test_name] = TestStatus.FAILED.value

    return test_status_map


def parse_log_ctest(log: str) -> dict[str, str]:
    """
    Parser for ctest test runner report.
    """
    # Test name to status map
    test_status_map = {}

    # Regex to match test result reporting lines from the log and to extract test name and status
    pattern = re.compile(r"^.*Test\s+#\d+:\s+(.*\.+)\s*(.*)\s+\d+\.\d+\s+sec$")

    # Split the log into multiple lines and extract the executed tests along with their statuses
    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            test_name, status = match.groups()
            test_name = test_name.strip(".").strip()
            status = status.strip().lower()
            if status == "passed":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "failed" or status.startswith("***"):
                test_status_map[test_name] = TestStatus.FAILED.value

    return test_status_map


def parse_log_doctest(log: str) -> dict[str, str]:
    """
    Parser for Doctest test execution report.

    Note:
    Individual sub-cases results are not parsed from the XML report, because the sub-cases can be
    nested to any arbitrary depth.
    """

    def parse_log_xml(log: str) -> dict[str, str]:
        """
        Parser for XML report.
        """

        def parse_testcase_section(section):
            """
            Get the name and the result of the given section, recursively parsing the nested sections.
            """
            # Current section name and result
            section_name = section.get("name", "<section>")
            section_expressions = section.findall("Expression")
            if section_expressions is not None:
                section_result = all(expr.get("success") == "true" for expr in section_expressions)
            else:
                section_result = True

            # Recursively parse nested section (if exists)
            nested_section = section.find("SubCase")
            if nested_section is not None:
                nested_section_name, nested_section_result = parse_testcase_section(nested_section)
                section_name = f"{section_name} > {nested_section_name}"
                section_result = section_result and nested_section_result

            return section_name, section_result

        # Test name to status map
        test_status_map = {}

        # Parse XML and extract tests and their statues
        root = ET.fromstring(log)

        for testcase in root.findall(".//TestCase"):
            # Ignore skipped testcase
            if testcase.get("skipped", "") == "true":
                continue
            testcase_name = testcase.get("name", "<testcase>")
            # Overall testcase result
            testcase_overall_result = testcase.find("OverallResultsAsserts")
            if testcase_overall_result is not None:
                testcase_passed = testcase_overall_result.get("test_case_success") == "true"
                if testcase_passed:
                    test_status_map[testcase_name] = TestStatus.PASSED.value
                else:
                    test_status_map[testcase_name] = TestStatus.FAILED.value
                # Sections results
                for section in testcase.findall("SubCase"):
                    section_name, section_passed = parse_testcase_section(section)
                    testcase_section_name = f"{testcase_name} > {section_name}"
                    if section_passed:
                        test_status_map[testcase_section_name] = TestStatus.PASSED.value
                    else:
                        test_status_map[testcase_section_name] = TestStatus.FAILED.value

        return test_status_map

    # XML log parser
    start_tag = "<doctest"
    end_tag = "</doctest>"
    start_index = log.find(start_tag)
    end_index = log.find(end_tag, start_index) + len(end_tag) if start_index != -1 else -1
    if start_index != -1 and end_index != -1:
        return parse_log_xml(log[start_index:end_index])

    # Fallback to ctest log parser
    return parse_log_ctest(log)


def parse_log_catch2(log: str) -> dict[str, str]:
    """
    Parser for Catch2 test execution report.

    Note:
    Individual sections results are not parsed from the XML report, because the sections can be
    nested to any arbitrary depth.
    """

    def parse_log_xml(log: str) -> dict[str, str]:
        """
        Parser for XML report.
        """

        def parse_testcase_section(section):
            """
            Get the name and the result of the given section, recursively parsing the nested sections.
            """
            # Current section name and result
            section_name = section.get("name", "<section>")
            section_expressions = section.findall("Expression")
            if section_expressions is not None:
                section_result = all(expr.get("success") == "true" for expr in section_expressions)
            else:
                section_result = True

            # Recursively parse nested section (if exists)
            nested_section = section.find("Section")
            if nested_section is not None:
                nested_section_name, nested_section_result = parse_testcase_section(nested_section)
                section_name = f"{section_name} > {nested_section_name}"
                section_result = section_result and nested_section_result

            return section_name, section_result

        # Test name to status map
        test_status_map = {}

        # Parse XML and extract tests and their statues
        root = ET.fromstring(log)

        for testcase in root.findall(".//TestCase"):
            testcase_name = testcase.get("name", "<testcase>")
            # Overall testcase result
            testcase_overall_result = testcase.find("OverallResult")
            if testcase_overall_result is not None:
                # Ignore skipped testcase
                if testcase_overall_result.get("status", "") == "skipped":
                    continue
                testcase_passed = testcase_overall_result.get("success") == "true"
                if testcase_passed:
                    test_status_map[testcase_name] = TestStatus.PASSED.value
                else:
                    test_status_map[testcase_name] = TestStatus.FAILED.value
                # Sections results
                for section in testcase.findall("Section"):
                    section_overall_result = section.find("OverallResults")
                    if section_overall_result is not None:
                        # Ignore skipped section
                        if section_overall_result.get("skipped", "") == "true":
                            continue
                    section_name, section_passed = parse_testcase_section(section)
                    testcase_section_name = f"{testcase_name} > {section_name}"
                    if section_passed:
                        test_status_map[testcase_section_name] = TestStatus.PASSED.value
                    else:
                        test_status_map[testcase_section_name] = TestStatus.FAILED.value

        return test_status_map

    # XML log parser
    start_tag = "<Catch2TestRun"
    end_tag = "</Catch2TestRun>"
    start_index = log.find(start_tag)
    end_index = log.find(end_tag, start_index) + len(end_tag) if start_index != -1 else -1
    if start_index != -1 and end_index != -1:
        return parse_log_xml(log[start_index:end_index])

    # Fallback to ctest log parser
    return parse_log_ctest(log)


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

    if test_status_map:
        return test_status_map

    # Fallback to ctest log parser
    return parse_log_ctest(log)

def parse_log_common(log: str) -> dict[str, str]:
    """
    Try all parsers and return if only one parser returns results or all result is the same.
    """
    parsers = [
        parse_log_googletest,
        parse_log_doctest,
        parse_log_catch2,
        parse_log_tap,
        parse_log_ctest,
    ]
    results = {}
    for parser in parsers:
        result = parser(log)
        print(f"Parser {parser.__name__} returned {len(result)} results.")
        print(result)
        if result:
            results[parser.__name__] = result

    if len(results) == 1:
        return list(results.values())[0]
    # Check if all results are the same
    first_result = None
    for result in results.values():
        print(f"Comparing result: {result}")
        print(first_result)
        print(f"Is equal: {result == first_result}")
        if first_result is None:
            first_result = result
        elif result != first_result:
            return {}
    return first_result if first_result is not None else {}


def get_c_parser_by_name(name: str):
    if name == "non_agentic":
        return parse_log_common
    if name == "googletest":
        return parse_log_googletest
    if name == "doctest":
        return parse_log_doctest
    if name == "catch2":
        return parse_log_catch2
    if name == "tap":
        return parse_log_tap
    return parse_log_ctest


MAP_REPO_TO_PARSER_C = {
    "redis/redis": parse_log_redis,
    "jqlang/jq": parse_log_jq,
    "nlohmann/json": parse_log_doctest,
    "micropython/micropython": parse_log_micropython_test,
    "valkey-io/valkey": parse_log_redis,
    "fmtlib/fmt": parse_log_googletest,
}
