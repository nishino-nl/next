import os

from enum import IntEnum

DEFAULT_VERION_FILE = "VERSION"
DEFAULT_STAGING_BRANCH = "develop"
DEFAULT_PRODUCTION_BRANCH = "master"


class VersionLevel(IntEnum):
    MAJOR = 0
    MINOR = 1
    PATCH = 2


class Environment(IntEnum):
    DEVELOPMENT = 0
    STAGING = 1
    PRODUCTION = 2


def bump_level_from_str(bump_level_str: VersionLevel) -> VersionLevel:
    return VersionLevel[bump_level_str.upper()]


def determine_next_version(current_version: tuple, bump_level: VersionLevel) -> tuple:
    """
    Determine next version, based on current version and bump-level.

    :param: current_version: the version to bump from.
    :param bump_level: the VersionLevel (IntEnum) to bump.
    :return: version after the bump has taken place.
    """
    major, minor, patch = current_version

    # define new version based on current version and bump-level (major|minor|patch)
    next_version = (
        major + 1 if bump_level is VersionLevel.MAJOR
        else major,
        minor + 1 if bump_level is VersionLevel.MINOR
        else 0 if bump_level < VersionLevel['MINOR']
        else minor,
        patch + 1 if bump_level is VersionLevel.PATCH
        else 0,
    )
    return next_version


def full_path(path):
    _path = path

    # make sure to use an absolute path
    if path[0] == ".":
        # when a relative path has been given
        raise Exception("Sorry, no relative paths allowed")
    # TODO: (also) handle relative paths from cwd
    elif path[0] == "~":
        # when a path in homedir has been given
        homedir = os.path.expanduser(path.split("/")[0])
        sub_dirs = "/".join(path.split("/")[1:])
        _path = os.path.join(homedir, sub_dirs)
    # TODO: (also) handle absolute paths

    return _path


def read_version(file_path: str = DEFAULT_VERION_FILE) -> tuple:
    try:
        with open(file_path) as f:
            return version_str_to_tpl(f.read().strip())
    except FileNotFoundError as err:
        print(err)


def version_tpl_to_str(version: tuple) -> str:
    return ".".join([str(s) for s in version])


def version_str_to_tpl(version: str) -> tuple:
    version = tuple(int(x) for x in version.split("."))
    return version


def write_version(version: tuple, file_path: str = DEFAULT_VERION_FILE) -> bool:
    try:
        with open(file_path, mode="w") as f:
            f.write(f"{version_tpl_to_str(version)}\n")
            return True
    except FileNotFoundError as err:
        print(err)
