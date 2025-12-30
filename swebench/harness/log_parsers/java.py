import re
import json
from swebench.harness.constants import TestStatus
from typing import Dict, Iterable, Tuple, Optional
from xml.etree import ElementTree as ET

def parse_log_maven_v2(log: str) -> dict[str, str]:
    """
    Parse Maven Surefire console output that looks like:

        [INFO] Running com.example.FooTest
        [ERROR] com.example.FooTest.testBar -- Time elapsed: 0.003 s <<< ERROR!
        [ERROR] com.example.FooTest.testBaz -- Time elapsed: 0.001 s
        ...
        [INFO] Results:
        [ERROR] Tests run: 2, Failures: 0, Errors: 1, Skipped: 0

    Every line that *starts* with '[INFO]' or '[ERROR]' and contains
    ' -- Time elapsed:' is treated as a single test-method result.

    Returns
    -------
    Dict[str, str]
        Mapping  "<fully-qualified-class>.<method>"  ->  TestStatus.{PASSED,FAILED}.value
    """
    test_status: dict[str, str] = {}

    # One regex to capture both PASS and FAIL lines.
    # group(1) = fully-qualified test method (class.method)
    #            May include parameterized test info with spaces, parentheses, brackets, etc.
    # group(2) = 'ERROR' or 'FAILURE' if present ⇒ test failed/errored
    #
    # Updated to capture test names that contain special characters in parameterized tests.
    # Handles formats like:
    #   - testFilter[meta.created eq "2025-11-06T19:56:02.452Z", true](53)
    #   - testNullability[class com.unboundid.scim2.common.utils.StaticUtils](1)
    #   - caseInsensitiveHeaders(Locale)[1]
    #
    # Optional [prefix] at start handles formats like: [core] [INFO] testName ...
    line_re = re.compile(
        r"^(?:\[[^\]]+\]\s+)?\[(?:INFO|ERROR|WARN(?:ING)?)\]\s+(.+?)\s+(?:--\s+)?Time elapsed:\s*[\d.]+\s*s(?:\s*<<<\s+(ERROR|FAILURE)!)?"
    )

    for raw in log.splitlines():
        m = line_re.match(raw.strip())
        if not m:
            continue

        fq_test = m.group(1).strip()

        # Skip summary lines (start with "Tests run:")
        if fq_test.startswith('Tests run:'):
            continue

        # Validate it looks like a test: must have at least one dot (package.class pattern)
        # and start with a valid Java identifier
        if '.' not in fq_test:
            continue
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\.', fq_test):
            continue

        failed_marker = m.group(2)

        status = TestStatus.FAILED.value if failed_marker else TestStatus.PASSED.value
        test_status[fq_test] = status

    return test_status

def parse_log_maven(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with 'mvn test'.
    Annoyingly maven will not print the tests that have succeeded. For this log
    parser to work, each test must be run individually, and then we look for
    BUILD (SUCCESS|FAILURE) in the logs.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    current_test_name = "---NO TEST NAME FOUND YET---"

    # Get the test name from the command used to execute the test.
    # Assumes we run evaluation with set -x
    test_name_pattern = r"^.*-Dtest=(\S+).*$"
    result_pattern = r"^.*BUILD (SUCCESS|FAILURE)$"

    for line in log.split("\n"):
        test_name_match = re.match(test_name_pattern, line.strip())
        if test_name_match:
            current_test_name = test_name_match.groups()[0]

        result_match = re.match(result_pattern, line.strip())
        if result_match:
            status = result_match.groups()[0]
            if status == "SUCCESS":
                test_status_map[current_test_name] = TestStatus.PASSED.value
            elif status == "FAILURE":
                test_status_map[current_test_name] = TestStatus.FAILED.value

    return test_status_map


def parse_log_ant(log: str) -> dict[str, str]:
    test_status_map = {}

    pattern = r"^\s*\[junit\]\s+\[(PASS|FAIL|ERR)\]\s+(.*)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            status, test_name = match.groups()
            if status == "PASS":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status in ["FAIL", "ERR"]:
                test_status_map[test_name] = TestStatus.FAILED.value

    return test_status_map


def parse_log_gradle_custom(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with 'gradle test'. Assumes that the
    pre-install script to update the gradle config has run.
    """
    test_status_map = {}

    pattern = r"^([^>].+)\s+(PASSED|FAILED)$"

    for line in log.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            test_name, status = match.groups()
            if status == "PASSED":
                test_status_map[test_name] = TestStatus.PASSED.value
            elif status == "FAILED":
                test_status_map[test_name] = TestStatus.FAILED.value

    return test_status_map

ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)

def merge_status(existing: Optional[str], new: str) -> str:
    """
    Prefer worst outcome when duplicates appear across files:
    FAILED > SKIPPED > PASSED
    """
    if existing is None:
        return new
    priority = {"FAILED": 3, "SKIPPED": 2, "PASSED": 1}
    return existing if priority[existing] >= priority[new] else new

def mk_id(classname: str, name: str) -> str:
    # Normalize a test identifier as "com.foo.BarTest.testMethod"
    return f"{classname}.{name}".strip()

# -------------------------------
# 1) Parse structured Gradle JSON lines (preferred if present)
# -------------------------------

JSON_PREFIX = "__TEST_JSON__ "

def parse_gradle_json_lines(log: str) -> Dict[str, str]:
    """
    Expects lines like:
      __TEST_JSON__ {"class":"com.a.FooTest","name":"testBar","status":"SUCCESS","time_sec":0.012}
    Also handles lines with prefixes like:
      [ant:jacocoReport] __TEST_JSON__ {...}
    Returns UPPERCASE status: PASSED/FAILED/SKIPPED
    """
    results: Dict[str, str] = {}
    for line in log.splitlines():
        line = line.strip()
        # Check if line contains the JSON prefix anywhere (not just at start)
        # This handles cases like "[ant:jacocoReport] __TEST_JSON__ {...}"
        if JSON_PREFIX not in line:
            continue
        prefix_idx = line.index(JSON_PREFIX)
        payload = line[prefix_idx + len(JSON_PREFIX):].strip()
        try:
            obj = json.loads(payload)
            cls = obj.get("class") or obj.get("classname") or ""
            name = obj.get("name") or ""
            status_raw = (obj.get("status") or "").upper()
            if not cls or not name:
                continue
            if status_raw in ("SUCCESS", "PASSED"):
                status = "PASSED"
            elif status_raw in ("FAILURE", "FAILED", "ERROR"):
                status = "FAILED"
            elif status_raw in ("SKIPPED", "IGNORE", "IGNORED"):
                status = "SKIPPED"
            else:
                # Unknown -> treat as FAILED to be conservative
                status = "FAILED"
            test_id = mk_id(cls, name)
            results[test_id] = merge_status(results.get(test_id), status)
        except json.JSONDecodeError:
            # ignore malformed JSON lines
            continue
    return results

# -------------------------------
# 2) Parse JUnit XML printed to STDOUT with markers (preferred if present)
# -------------------------------

XML_BEGIN_BLOCK = "__JUNIT_XML_BEGIN__"
XML_FILE_BEGIN = "__JUNIT_XML_FILE_BEGIN__"
XML_FILE_END = "__JUNIT_XML_FILE_END__"
XML_END_BLOCK = "__JUNIT_XML_END__"

# Match markers even when they appear inside xtrace like:
# + echo '__JUNIT_XML_FILE_BEGIN__ /path.xml'
# But we need to avoid matching markers that are part of bash command lines
# Real markers appear on their own line or after echo/printf commands that were executed
FILE_BEGIN_RE = re.compile(r"__JUNIT_XML_FILE_BEGIN__\s+([^\r\n]+)")
FILE_END_RE   = re.compile(r"__JUNIT_XML_FILE_END__\s+([^\r\n]+)")

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s

def _sanitize_xml_text(xml: str) -> str:
    """
    - Remove bash xtrace lines inside the captured region
    - Trim to the first '<' and last '>' to avoid stray characters
    """
    # Drop obvious xtrace command lines
    cleaned_lines = []
    for line in xml.splitlines():
        ls = line.lstrip()
        # Examples we remove from within the XML block, if present accidentally
        if ls.startswith("+ ") and (" echo " in ls or " printf " in ls):
            continue
        cleaned_lines.append(line)
    xml = "\n".join(cleaned_lines)

    # Trim to XML-looking bounds
    start = xml.find("<")
    end = xml.rfind(">")
    if start != -1 and end != -1 and end >= start:
        xml = xml[start : end + 1]
    return xml.strip()

def iter_junit_xml_strings_from_log(log: str) -> Iterable[Tuple[str, str]]:
    """
    Robustly extract (path, xml_string) pairs between FILE_BEGIN/FILE_END markers.
    Handles:
      - markers printed as plain lines
      - markers appearing inside xtrace lines: + echo '__JUNIT_XML_FILE_BEGIN__ /path'
      - 'END' marker text appended to the same line as the closing tag due to xtrace
      - optional global BEGIN/END wrappers (not required)
    """
    s = strip_ansi(log)

    pos = 0
    max_iterations = len(s) // 100 + 1000  # Safety limit: reasonable max based on log size
    iteration_count = 0
    
    while True:
        iteration_count += 1
        if iteration_count > max_iterations:
            # Safety break to prevent infinite loops
            break
        
        m_begin = FILE_BEGIN_RE.search(s, pos)
        if not m_begin:
            break

        path_raw = m_begin.group(1)
        path = _strip_quotes(path_raw)

        # Skip false matches from xtrace lines where the marker appears in a bash command string.
        # Real file paths should not contain certain shell metacharacters or look like command fragments.
        # Examples of false matches: '$file"; cat "$file"; echo "__JUNIT_XML_FILE_END__'
        # Note: Java inner classes use $ (e.g., Foo$Bar.xml) so we need to be careful with $ detection
        
        # Check if this marker is part of a bash command line (xtrace shows the command being executed)
        # Look backwards to see if this is in a command context
        marker_start = m_begin.start()
        line_start = s.rfind('\n', max(0, marker_start - 500), marker_start)
        if line_start == -1:
            line_start = 0
        line_before_marker = s[line_start:marker_start]
        
        # If the line contains command syntax like "; cat" or "done <" before the marker,
        # this is likely a command line, not actual output
        is_command_line = (
            '; cat' in line_before_marker or
            '; echo' in line_before_marker or
            'done <' in line_before_marker or
            ('$' in line_before_marker and ('file' in line_before_marker or 'abs' in line_before_marker))
        )
        
        # Also check the path itself for command fragments
        has_command_fragments = (
            any(char in path for char in [';', '"', "'", '`', '&&', '||']) or
            (' -D' in path) or (' done' in path) or (' echo' in path) or
            (' cat ' in path) or (' exit ' in path) or
            ('$abs' in path and ';' in path) or  # Command substitution
            ('$file' in path and ';' in path)     # Command substitution
        )
        
        if is_command_line or has_command_fragments:
            # This is likely a bash command fragment from xtrace, skip it
            new_pos = m_begin.end()
            # Safety check: ensure we always advance
            if new_pos <= pos:
                pos = pos + 1  # Force advancement to prevent infinite loop
            else:
                pos = new_pos
            continue

        # Start content after the newline following the begin marker line (or its xtrace)
        nl_after_begin = s.find("\n", m_begin.end())
        if nl_after_begin == -1:
            # No newline after begin; nothing to capture
            break
        content_start = nl_after_begin + 1

        # If the very next line is the *printed* begin marker (after xtrace), skip it
        next_nl = s.find("\n", content_start)
        first_line = s[content_start: (next_nl if next_nl != -1 else content_start + 200)]
        if XML_FILE_BEGIN in first_line:
            # Skip that line too
            content_start = (next_nl + 1) if next_nl != -1 else content_start

        # Find the end marker after content_start
        m_end = FILE_END_RE.search(s, content_start)
        if not m_end:
            # Heuristic fallback: try to cut at the last plausible closing tag before next BEGIN or end of log
            # (prevents accidental inclusion of xtrace text after the XML)
            next_begin = FILE_BEGIN_RE.search(s, content_start)
            search_upto = next_begin.start() if next_begin else len(s)
            # Prefer </testsuite>, else </testsuites>
            end_tag_idx = s.rfind("</testsuite>", content_start, search_upto)
            if end_tag_idx == -1:
                end_tag_idx = s.rfind("</testsuites>", content_start, search_upto)
            if end_tag_idx != -1:
                xml_text = s[content_start : end_tag_idx + len("</testsuite>")]
                yield (path, _sanitize_xml_text(xml_text))
            else:
                # No closing tag found - try to extract up to the next BEGIN marker or end of log
                # This handles cases where XML might be incomplete but still contains testcases
                xml_text = s[content_start : search_upto]
                sanitized = _sanitize_xml_text(xml_text)
                # Only yield if it looks like valid XML (contains testcase elements)
                if '<testcase' in sanitized:
                    yield (path, sanitized)
            # Move on from where we started to avoid infinite loops
            # Safety check: ensure we always advance past the current marker
            new_pos = max(content_start, m_begin.end() + 1)
            if new_pos <= pos:
                # If we somehow didn't advance, force advancement to prevent infinite loop
                pos = pos + 1
            else:
                pos = new_pos
            continue

        # Normal case: slice content up to the start of END marker (even if END is inside an xtrace line)
        content_end = m_end.start()
        xml_text = s[content_start:content_end]
        xml_text = _sanitize_xml_text(xml_text)
        yield (path, xml_text)

        # Continue after the end marker
        pos = m_end.end()

def _parse_testcase_with_regex_fallback(xml_text: str) -> Dict[str, str]:
    """
    Fallback parser using regex to extract testcases when XML parsing fails.
    This ensures we don't lose tests due to XML parsing errors.
    Handles XML entities and testcases with attributes in any order.
    """
    results: Dict[str, str] = {}
    
    # Pattern 1: classname before name
    pattern1 = re.compile(
        r'<testcase[^>]*classname\s*=\s*["\']([^"\']+)["\'][^>]*name\s*=\s*["\']([^"\']+)["\']',
        re.MULTILINE | re.DOTALL
    )
    
    # Pattern 2: name before classname
    pattern2 = re.compile(
        r'<testcase[^>]*name\s*=\s*["\']([^"\']+)["\'][^>]*classname\s*=\s*["\']([^"\']+)["\']',
        re.MULTILINE | re.DOTALL
    )
    
    def decode_xml_entities(s: str) -> str:
        """Decode common XML entities"""
        return (s.replace('&apos;', "'")
                 .replace('&quot;', '"')
                 .replace('&amp;', '&')
                 .replace('&lt;', '<')
                 .replace('&gt;', '>'))
    
    def extract_testcase_status(xml_text: str, start_pos: int, end_pos: int) -> str:
        """Extract test status from testcase element and nearby context"""
        # Look at the testcase element itself
        elem_start = max(0, start_pos - 100)
        elem_end = min(len(xml_text), end_pos + 500)  # Look ahead for child elements
        context = xml_text[elem_start:elem_end]
        
        # Check for child elements that indicate status
        # Look for <skipped>, <failure>, or <error> tags (may be on same line or next lines)
        if re.search(r'<skipped\s*/?>', context, re.IGNORECASE):
            return "SKIPPED"
        if re.search(r'<(failure|error)\s*/?>', context, re.IGNORECASE):
            return "FAILED"
        return "PASSED"
    
    # Try pattern 1 (classname before name)
    for match in pattern1.finditer(xml_text):
        cls = match.group(1)
        name = match.group(2)
        if cls and name and '.' in cls:  # Validate it looks like a classname
            cls = decode_xml_entities(cls).strip()
            name = decode_xml_entities(name).strip()
            
            start_pos = match.start()
            end_pos = xml_text.find('>', start_pos)
            if end_pos == -1:
                end_pos = start_pos + 500  # Fallback
            
            status = extract_testcase_status(xml_text, start_pos, end_pos)
            test_id = mk_id(cls, name)
            results[test_id] = merge_status(results.get(test_id), status)
    
    # Try pattern 2 (name before classname)
    for match in pattern2.finditer(xml_text):
        name = match.group(1)
        cls = match.group(2)
        if cls and name and '.' in cls:  # Validate it looks like a classname
            cls = decode_xml_entities(cls).strip()
            name = decode_xml_entities(name).strip()
            
            start_pos = match.start()
            end_pos = xml_text.find('>', start_pos)
            if end_pos == -1:
                end_pos = start_pos + 500  # Fallback
            
            status = extract_testcase_status(xml_text, start_pos, end_pos)
            test_id = mk_id(cls, name)
            results[test_id] = merge_status(results.get(test_id), status)
    
    return results

def parse_junit_xml_string(xml_text: str) -> Dict[str, str]:
    """
    Parse a JUnit XML document (testsuite or testsuites) and return { "class.method": STATUS }.
    STATUS ∈ {PASSED, FAILED, SKIPPED}
    
    Uses ElementTree first, with regex fallback if XML parsing fails to ensure no tests are lost.
    """
    results: Dict[str, str] = {}
    xml_text = xml_text.strip()
    if not xml_text:
        return results

    # Try ElementTree parsing first (preferred method)
    root = None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # As a last chance, try trimming to the first '<' and last '>'
        xml_text2 = _sanitize_xml_text(xml_text)
        try:
            root = ET.fromstring(xml_text2)
            xml_text = xml_text2  # Use sanitized version
        except ET.ParseError:
            # XML parsing failed completely - use regex fallback
            return _parse_testcase_with_regex_fallback(xml_text)

    if root is None:
        return _parse_testcase_with_regex_fallback(xml_text)

    # Support either <testsuite> or <testsuites>
    testcases = root.findall(".//testcase")
    
    # If ElementTree found no testcases but we have XML content with testcase elements, try regex fallback
    if not testcases and '<testcase' in xml_text:
        regex_results = _parse_testcase_with_regex_fallback(xml_text)
        if regex_results:
            return regex_results

    # Parse testcases found by ElementTree
    for tc in testcases:
        cls = (tc.attrib.get("classname") or "").strip()
        name = (tc.attrib.get("name") or "").strip()
        if not cls or not name:
            continue

        # Determine status by presence of child elements
        status = "PASSED"
        if tc.find("skipped") is not None:
            status = "SKIPPED"
        if tc.find("failure") is not None or tc.find("error") is not None:
            status = "FAILED"

        results[mk_id(cls, name)] = merge_status(results.get(mk_id(cls, name)), status)

    # Supplement with regex to catch any testcases ElementTree might have missed
    # This is safer than relying solely on ElementTree, which can miss testcases
    # even when it successfully parses (e.g., due to XML structure issues)
    # We only add tests from regex that ElementTree didn't already find
    regex_results = _parse_testcase_with_regex_fallback(xml_text)
    for test_id, status in regex_results.items():
        if test_id not in results:
            # ElementTree missed this test - add it from regex
            results[test_id] = status
        else:
            # ElementTree found it - keep ElementTree's result (more reliable for status)
            pass

    return results

def parse_junit_xml_blocks_from_log(log: str) -> Dict[str, str]:
    collected: Dict[str, str] = {}
    for _path, xml_text in iter_junit_xml_strings_from_log(log):
        per_file = parse_junit_xml_string(xml_text)
        for k, v in per_file.items():
            collected[k] = merge_status(collected.get(k), v)
    return collected

# -------------------------------
# Orchestrator: try in order → JSON lines, XML, console
# -------------------------------

def parse_ci_log(log: str) -> Dict[str, str]:
    """
    Preferred order:
      1) Structured Gradle JSON lines (fastest, most precise)
      2) JUnit XML blocks printed to stdout
      3) Fallback console regex (Maven/Gradle)
    """
    # 1) Gradle JSON lines (works only if your Gradle init script was used)
    json_results = parse_gradle_json_lines(log)
    if json_results:
        return json_results

    # 2) Inline JUnit XML blocks (works for both Maven & Gradle if you printed them)
    xml_results = parse_junit_xml_blocks_from_log(log)
    if xml_results:
        return xml_results

    # 3) Fallback to console parsing (try Maven then Gradle; merge)
    maven_results = parse_log_maven_v2(log)
    gradle_results = parse_log_gradle_custom(log)

    # Merge (prefer failures)
    merged: Dict[str, str] = {}
    for k, v in {**maven_results, **gradle_results}.items():
        merged[k] = merge_status(merged.get(k), v)

    return merged

def get_java_parser_by_name(name: str):
    if name=="maven":
        return parse_ci_log
    if name=="ant":
        return parse_log_ant
    if name=="gradle":
        return parse_ci_log
    return parse_ci_log


MAP_REPO_TO_PARSER_JAVA = {
    "google/gson": parse_log_maven_v2,
    "apache/druid": parse_log_maven,
    "javaparser/javaparser": parse_log_maven,
    "projectlombok/lombok": parse_log_ant,
    "apache/lucene": parse_log_gradle_custom,
    "reactivex/rxjava": parse_log_gradle_custom,
    "apache/commons-lang": parse_log_maven_v2,
    "spring-projects/spring-framework": parse_log_gradle_custom
}
