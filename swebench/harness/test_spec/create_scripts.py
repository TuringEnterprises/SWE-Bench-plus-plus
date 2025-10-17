from swebench.harness.constants import MAP_REPO_TO_EXT, get_ext_from_language
from swebench.harness.test_spec.c import (
    make_eval_script_list_c
)
from swebench.harness.test_spec.java import (
    make_eval_script_list_java
)
from swebench.harness.test_spec.php import (
    make_eval_script_list_php
)
from swebench.harness.test_spec.rust import (
    make_eval_script_list_rust
)
from swebench.harness.test_spec.go import (
    make_eval_script_list_go
)
from swebench.harness.test_spec.javascript import (
    make_eval_script_list_js,
)
from swebench.harness.test_spec.python import (
    make_repo_script_list_py,
    make_env_script_list_py,
    make_eval_script_list_py,
)
from swebench.harness.test_spec.ruby import (
    make_eval_script_list_ruby
)
from swebench.harness.test_spec.utils import (
    make_env_script_list_common,
    make_eval_script_list_common,
    make_repo_script_list_common,
)


def make_repo_script_list(specs, repo, repo_directory, base_commit, env_name, language="Python") -> list:
    """
    Create a list of bash commands to set up the repository for testing.
    This is the setup script for the instance image.
    """
    
    ext = MAP_REPO_TO_EXT.get(repo)
    if not ext:
        ext = get_ext_from_language(language)

    func = {
        "py": make_repo_script_list_py,
    }.get(ext, make_repo_script_list_common)
    return func(specs, repo, repo_directory, base_commit, env_name)


def make_env_script_list(instance, specs, env_name) -> list:
    """
    Creates the list of commands to set up the environment for testing.
    This is the setup script for the environment image.
    """
    ext = MAP_REPO_TO_EXT.get(instance["repo"])
    if not ext:
        ext = get_ext_from_language(instance["language"])
    func = {
        "py": make_env_script_list_py,
    }.get(ext, make_env_script_list_common)
    return func(instance, specs, env_name)


def make_eval_script_list(
    instance, specs, env_name, repo_directory, base_commit, test_patch, run_all_tests=False
) -> list:
    """
    Applies the test patch and runs the tests.
    """
    ext = MAP_REPO_TO_EXT.get(instance["repo"])
    if not ext:
        ext = get_ext_from_language(instance["language"])
    common_func = make_eval_script_list_common
    func = {
        "c": make_eval_script_list_c,
        "rust": make_eval_script_list_rust,
        "php": make_eval_script_list_php,
        "js": make_eval_script_list_js,
        "ts": make_eval_script_list_js,
        "py": make_eval_script_list_py,
        "java": make_eval_script_list_java,
        "go": make_eval_script_list_go,
        "rb": make_eval_script_list_ruby
    }.get(ext, common_func)
    return func(instance, specs, env_name, repo_directory, base_commit, test_patch, run_all_tests)
