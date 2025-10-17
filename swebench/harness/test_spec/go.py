from swebench.harness.constants import (
    END_TEST_OUTPUT,
    START_TEST_OUTPUT,
)
from swebench.harness.utils import get_modified_files
import os
import re
from pathlib import Path
from collections import defaultdict

# Extensions we never want to treat as tests
NON_TEST_EXTS = (
    ".md", ".txt", ".png", ".jpg", ".gif", ".svg",
    ".json", ".yml", ".yaml", ".xml",
)

def get_test_directives(instance) -> list[str]:
    """
    Given a SWE-bench task `instance`, return CLI fragments to append to a `go test`
    command that will run only the test packages modified in the PR.

    Returns
    -------
    list[str]
        A list of local package paths prefixed with './', e.g.:
            ["./test/utils/image", "./staging/src/k8s.io/kubectl/pkg/cmd/create"]
        If no relevant Go test files are changed, returns [].
    """
    diff_pat = r"diff --git a/.* b/(.*)"
    changed_paths = re.findall(diff_pat, instance["test_patch"])

    # Filter for Go files that are likely related to tests
    test_paths = [
        p for p in changed_paths
        if p.endswith(".go") and (
            "_test.go" in p or "test" in p or "/test/" in p
        )
    ]

    if not test_paths:
        return []

    # Normalize to package directory paths, prefixed with './'
    pkg_paths = {
        f'./{os.path.dirname(p)}' if os.path.dirname(p) else '.' for p in test_paths
    }

    return sorted(pkg_paths)



def make_eval_script_list_go(
    instance, specs, env_name, repo_directory, base_commit, test_patch, run_all_tests
) -> list:
    """
    Applies the test patch and runs the tests.
    """
    HEREDOC_DELIMITER = "EOF_114329324912"
    test_files = get_modified_files(test_patch)
    # Reset test files to the state they should be in before the patch.
    if test_files:
        reset_tests_command = f"git checkout {base_commit} {' '.join(test_files)}"
    else:
        reset_tests_command = 'echo "No test files to reset"'

    build_commands = []
    if "build" in specs:
        build_commands.extend(specs["build"])

    apply_test_patch_command = f"git apply --verbose --reject - <<'{HEREDOC_DELIMITER}'\n{test_patch}\n{HEREDOC_DELIMITER}"

    base_cmd = specs.get("test_cmd")
    no_test_directives = specs.get("no_test_directives", False)
    if run_all_tests or no_test_directives:
        directives = []
    else:
        directives = get_test_directives(instance)
    test_commands = " ".join([base_cmd, *directives])
    
    eval_commands = [
        f"cd {repo_directory}",
        f"git config --global --add safe.directory {repo_directory}",  # for nonroot user
        f"cd {repo_directory}",
        # This is just informational, so we have a record
        # f"git status",
        # f"git show",
        # f"git -c core.fileMode=false diff {base_commit}",
        reset_tests_command,
        apply_test_patch_command,
        *build_commands,
        f": '{START_TEST_OUTPUT}'",
        test_commands,
        f": '{END_TEST_OUTPUT}'",
        reset_tests_command,
    ]
    return eval_commands
