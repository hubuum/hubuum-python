#!/usr/bin/env python
"""Prepare a release of the project.

This script is used to prepare a release of the project. It prompts the user for a
semantic version, updates the version string in pyproject.toml and in hubuum/__init__.py,
and performes a git commit and tags the commit with the new version.

Afterwards the user may push the commit and tag to the remote repository, which should
trigger a GitHub Actions workflow to build and publish the package to PyPI.
"""

import argparse
import os
import re
import subprocess
from typing import Optional, Tuple

SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
PYPROJECT_FILENAME = "pyproject.toml"
TARGET_VARIABLE = "TAG_VERSION"


def parse_arguments() -> Tuple[bool, Optional[str]]:
    """Parse command-line arguments.

    :returns: A tuple containing a boolean flag for the --dirty option and the version string.
    """
    parser = argparse.ArgumentParser(description="Prepare a release of the project.")
    parser.add_argument(
        "--dirty",
        "-d",
        action="store_true",
        help="Allow the working directory to be dirty.",
    )
    parser.add_argument(
        "version",
        nargs="?",
        default=None,
        help="Semantic version for the release.",
    )
    args = parser.parse_args()

    return args.dirty, args.version


def remove_special_chars(input_str: str, chars_to_remove: str) -> str:
    """Remove specific characters from a string.

    Given a string and a set of characters to remove, this function returns a new
    string with those characters removed.

    :param input_str: The original string from which to remove characters.
    :param chars_to_remove: A string containing characters to be removed.

    :returns: A new string with specified characters removed.
    """
    return "".join(char for char in input_str if char not in chars_to_remove)


def is_semver(tag: str) -> bool:
    """Check if the tag is a valid semantic version.

    :param tag: The tag to validate.

    :returns: True if the tag is a valid semantic version, False otherwise.
    """
    return bool(re.match(SEMVER_PATTERN, tag))


def is_working_tree_clean() -> bool:
    """Check if the git working tree is clean.

    :returns: True if the working tree is clean, False otherwise.
    """
    return (
        subprocess.run(
            ["git", "diff", "--exit-code"], capture_output=True, text=True
        ).returncode
        == 0
    )


def find_init_py() -> Optional[str]:
    """Find the __init__.py file for the project.

    :returns: Path to __init__.py file if found, otherwise None.
    """
    project_name = os.path.basename(os.getcwd())
    for root, _, files in os.walk("."):
        if "__init__.py" in files and project_name in root:
            return os.path.join(root, "__init__.py")
    return None


def update_variable_in_file(version: str, file_path: str, pattern: str) -> None:
    """Update version string in a given file.

    :param version: The new version string.
    :param file_path: Path to the file to update.
    :param pattern: The pattern to search for in the file to replace.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    target_string = remove_special_chars(pattern, "^")

    for i, line in enumerate(lines):
        if re.search(pattern, line):
            lines[i] = f'{target_string} "{version}"\n'

    with open(file_path, "w") as f:
        f.writelines(lines)


def main() -> None:
    """Execute the main script."""
    dirty, version = parse_arguments()

    if not dirty and not is_working_tree_clean():
        print("Working tree is not clean. Commit or stash changes before running.")
        return

    version = version if version else input("Enter a valid semantic version: ").strip()

    if not is_semver(version):
        print("Invalid semantic version.")
        return

    update_variable_in_file(version, "pyproject.toml", r"^version =")
    subprocess.run(["git", "add", PYPROJECT_FILENAME])

    init_path = find_init_py()
    if init_path:
        update_variable_in_file(version, init_path, r"^TAG_VERSION =")
        subprocess.run(["git", "add", init_path])

    diff_output = subprocess.check_output(["git", "diff", "--cached"], text=True)
    print(diff_output)

    confirm = input("Are these changes okay? (yes/no): ").strip().lower()

    if confirm == "yes":
        subprocess.run(["git", "commit", "-m", f"Release {version}"])
        subprocess.run(["git", "tag", f"v{version}"])
        print("Changes committed and tagged.")
    else:
        subprocess.run(["git", "reset"])
        subprocess.run(["git", "checkout", "--", "pyproject.toml", init_path])
        print("Changes not committed and reverted.")


if __name__ == "__main__":
    main()
