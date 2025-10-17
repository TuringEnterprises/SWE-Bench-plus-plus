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
from pathlib import Path
import json
import sys

def get_cli_arg(name: str) -> str | None:
    if name in sys.argv:
        idx = sys.argv.index(name)
        try:
            value = sys.argv[idx + 1]
            if not value.startswith("--"):  # ensure it's not another flag
                return value
        except IndexError:
            pass  # flag was last element, no value
    return None


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

# Always try to load from dataset.json (default behavior)
dataset_path = get_cli_arg("--dataset_name")
if dataset_path and dataset_path.endswith(".json") and dataset_path.endswith(".jsonl"):
    if dataset_path.endswith(".json"):
        dataset = json.loads(Path(dataset_path).read_text())
        if type(dataset)!=list:
            dataset = [dataset]
    elif dataset_path.endswith(".jsonl"):
        dataset = [json.loads(line) for line in Path(dataset_path).read_text().splitlines()]

    MAP_REPO_TO_PARSER = {}
    for instance in dataset:
        repo_name = instance["repo"]
        language = instance["language"]
        repo_specs = instance["spec_dict"]
        log_parser_name = repo_specs.get("log_parser_name", "")

        if log_parser_name == "custom":
            log_parser = repo_specs.get("log_parser_code")
            if log_parser:
                MAP_REPO_TO_PARSER[repo_name] = log_parser
            else:
                MAP_REPO_TO_PARSER[repo_name] = LANGUAGE_PARSER_MAP[language](log_parser_name)
        else:
            MAP_REPO_TO_PARSER[repo_name] = LANGUAGE_PARSER_MAP[language](log_parser_name)

else:
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
]
