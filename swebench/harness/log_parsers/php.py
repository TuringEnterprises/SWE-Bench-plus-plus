import re
from swebench.harness.constants import TestStatus

def parse_log_phpunit(log: str) -> dict[str, str]:
    """
    Parser for phpunit logs with the --testdox option.
    Args:
        log (str): log content
        test_spec (TestSpec): test spec (unused)
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    suite = None

    suite_pattern = r"^(\w.+) \(.+\)$"
    test_pattern = r"^\s*([✔✘↩])\s*(.*)$"

    for line in log.split("\n"):
        suite_match = re.match(suite_pattern, line)
        if suite_match:
            suite = suite_match.groups()[0]
            continue

        test_match = re.match(test_pattern, line)
        if test_match:
            status, test_name = test_match.groups()
            full_test_name = f"{suite} > {test_name}"

            if status == "✔":
                test_status_map[full_test_name] = TestStatus.PASSED.value
            elif status == "✘":
                test_status_map[full_test_name] = TestStatus.FAILED.value
            elif status == "↩":
                test_status_map[full_test_name] = TestStatus.SKIPPED.value

    return test_status_map

def get_php_parser_by_name(name: str):
    if name=="phpunit":
        return parse_log_phpunit
    return parse_log_phpunit

MAP_REPO_TO_PARSER_PHP = {
    "phpoffice/phpspreadsheet": parse_log_phpunit,
    "laravel/framework": parse_log_phpunit,
    "php-cs-fixer/php-cs-fixer": parse_log_phpunit,
    "briannesbitt/carbon": parse_log_phpunit,
}
