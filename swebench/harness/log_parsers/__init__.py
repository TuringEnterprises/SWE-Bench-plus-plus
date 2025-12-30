from swebench.harness.log_parsers.c import MAP_REPO_TO_PARSER_C, get_c_parser_by_name
from swebench.harness.log_parsers.go import MAP_REPO_TO_PARSER_GO, get_go_parser_by_name
from swebench.harness.log_parsers.java import MAP_REPO_TO_PARSER_JAVA, get_java_parser_by_name
from swebench.harness.log_parsers.javascript import MAP_REPO_TO_PARSER_JS, get_js_parser_by_name
from swebench.harness.log_parsers.php import MAP_REPO_TO_PARSER_PHP, get_php_parser_by_name
from swebench.harness.log_parsers.python import MAP_REPO_TO_PARSER_PY, get_py_parser_by_name
from swebench.harness.log_parsers.ruby import MAP_REPO_TO_PARSER_RUBY, get_ruby_parser_by_name
from swebench.harness.log_parsers.rust import MAP_REPO_TO_PARSER_RUST, get_rust_parser_by_name
from swebench.harness.log_parsers.csharp import MAP_REPO_TO_PARSER_CS, get_cs_parser_by_name
from swebench.harness.constants.__init__ import C_SBP_STR, GO_SBP_STR, PHP_SBP_STR, JAVA_SBP_STR, RUBY_SBP_STR, RUST_SBP_STR, PYTHON_SBP_STR, JAVASCRIPT_SBP_STR, TYPESCRIPT_SBP_STR, C_PLUS_SBP_STR, CSHARP_SBP_STR


LANGUAGE_PARSER_MAP = {
    C_SBP_STR: get_c_parser_by_name,
    CSHARP_SBP_STR: get_cs_parser_by_name,
    C_PLUS_SBP_STR: get_c_parser_by_name,
    JAVA_SBP_STR: get_java_parser_by_name,
    GO_SBP_STR: get_go_parser_by_name,
    JAVASCRIPT_SBP_STR: get_js_parser_by_name,
    TYPESCRIPT_SBP_STR: get_js_parser_by_name,
    PHP_SBP_STR: get_php_parser_by_name,
    PYTHON_SBP_STR: get_py_parser_by_name,
    RUST_SBP_STR: get_rust_parser_by_name,
    RUBY_SBP_STR: get_ruby_parser_by_name
}

# Static repo-to-parser map for backward compatibility fallback
# Note: With the new TestSpec.log_parser field, this is only used as a fallback
# when TestSpec doesn't have a log_parser set (e.g., legacy code paths)
MAP_REPO_TO_PARSER = {
    **MAP_REPO_TO_PARSER_C,
    **MAP_REPO_TO_PARSER_GO,
    **MAP_REPO_TO_PARSER_JAVA,
    **MAP_REPO_TO_PARSER_JS,
    **MAP_REPO_TO_PARSER_PHP,
    **MAP_REPO_TO_PARSER_PY,
    **MAP_REPO_TO_PARSER_RUST,
    **MAP_REPO_TO_PARSER_CS,
    **MAP_REPO_TO_PARSER_RUBY,
}


__all__ = [
    "MAP_REPO_TO_PARSER",
    "LANGUAGE_PARSER_MAP",
]
