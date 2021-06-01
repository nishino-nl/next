import os


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


def read_version(file_path: str = "VERSION") -> tuple:
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


def write_version(version: tuple, file_path: str = "VERSION") -> bool:
    try:
        with open(file_path, mode="w") as f:
            f.write(f"{version_tpl_to_str(version)}\n")
            return True
    except FileNotFoundError as err:
        print(err)
