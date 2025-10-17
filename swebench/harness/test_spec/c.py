from swebench.harness.constants import (
    END_TEST_OUTPUT,
    START_TEST_OUTPUT,
)
from swebench.harness.utils import get_modified_files


def get_test_directives(instance) -> list[str]:
    """
    Get test directives from the test_patch of a task instance

    Args:
        instance (dict): task instance
    Returns:
        directives (list): List of test directives
    """
    # Not supported yet
    return []


def make_eval_script_list_c(
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

    apply_test_patch_command = (
        f"git apply --verbose --reject - <<'{HEREDOC_DELIMITER}'\n{test_patch}\n{HEREDOC_DELIMITER}"
    )

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
