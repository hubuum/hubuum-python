import os
import re
import subprocess
from typing import Dict, Optional

import toml

SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
PYPROJECT_FILENAME = "pyproject.toml"
TARGET_VARIABLE = "TAG_VERSION"


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


def load_pyproject_toml() -> Dict[str, str]:
    """Load the pyproject.toml file.

    :returns: The content of pyproject.toml as a dictionary.
    """
    with open(PYPROJECT_FILENAME, "r") as f:
        return toml.load(f)


def save_pyproject_toml(data: Dict[str, str]) -> None:
    """Save data to pyproject.toml file.

    :param data: The data to save.
    """
    with open(PYPROJECT_FILENAME, "w") as f:
        toml.dump(data, f)


def find_init_py() -> Optional[str]:
    """Find the __init__.py file for the project.

    :returns: Path to __init__.py file if found, otherwise None.
    """
    project_name = os.path.basename(os.getcwd())
    for root, _, files in os.walk("."):
        if "__init__.py" in files and project_name in root:
            return os.path.join(root, "__init__.py")
    return None


def update_version_in_file(version: str, file_path: str, pattern: str) -> None:
    """Update version string in a given file.

    :param version: The new version string.
    :param file_path: Path to the file to update.
    :param pattern: The pattern to search for in the file to replace.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if re.search(pattern, line):
            lines[i] = f'{TARGET_VARIABLE} = "{version}"\n'

    with open(file_path, "w") as f:
        f.writelines(lines)


def main() -> None:
    if not is_working_tree_clean():
        print("Working tree is not clean. Commit or stash changes before running.")
        return

    version = input("Enter a valid semantic version: ").strip()

    if not is_semver(version):
        print("Invalid semantic version.")
        return

    pyproject_data = load_pyproject_toml()
    pyproject_data["tool"]["poetry"]["version"] = version
    save_pyproject_toml(pyproject_data)
    subprocess.run(["git", "add", PYPROJECT_FILENAME])

    init_path = find_init_py()
    if init_path:
        update_version_in_file(version, init_path, r"^VERSION =")
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
        print("Changes not committed.")


if __name__ == "__main__":
    main()
