"""The hubuum package."""

import subprocess
import sys
from typing import Dict

import django
import django_filters
import rest_framework

ASSUMED_RELEASE = "0.1.0"


# Covering this is annoying as different python versions have different
# ways of getting module versions.
def get_module_versions() -> Dict[str, str]:  # pragma: no cover
    """Get the versions for all installed modules.

    :raises: None. All exceptions are caught and handled internally.

    :returns: Versions of the module as a Dict[str, str].
    """
    module_versions: Dict[str, str] = {}

    try:
        from importlib.metadata import distributions  # noqa

        for dist in distributions():
            module_versions[dist.metadata["Name"]] = dist.version

        return module_versions
    except ImportError:
        pass

    try:
        import pkg_resources  # noqa

        for module in pkg_resources.working_set:
            module_versions[module.project_name] = module.version

        return module_versions

    except ImportError:
        pass

    return module_versions


# Get the version number.
# Check if we're in a git repo, and if we are, get the build number via
# git describe --all --match 'v[0-9]*' --long --dirty --always
# If we are NOT in a git repo, return ASSUMED_RELEASE
def get_version() -> str:
    """Get the version via git."""
    try:
        cmd = "git describe --all --match 'v[0-9]*' --long --dirty --always"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out, _ = p.communicate()
        if out:
            return out.decode().strip()
        else:  # pragma: no cover
            return ASSUMED_RELEASE
    except Exception:
        return ASSUMED_RELEASE


def get_build() -> str:
    """Get the version number based on the build."""
    try:
        cmd = "git log -n 1 --pretty=format:'%H'"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out, _ = p.communicate()
        if out:
            return out.decode().strip()
        else:  # pragma: no cover
            return ""
    except Exception:  # pragma: no cover
        return ""


__build__ = get_build()
__version__ = get_version()
BUILD = __build__
VERSION = __version__

module_versions = get_module_versions()
config = {}  # This will be set in apps.py

debug = {
    "module_versions": get_module_versions(),
    "config": config,
}

runtimes = {
    "python": sys.version,
    "django": django.get_version(),
    "rest_framework": rest_framework.VERSION,
    "django-rest-knox": module_versions["django-rest-knox"],
    "django_filters": django_filters.__version__,
}
