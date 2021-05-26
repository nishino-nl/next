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

    return _path
