#!/usr/bin/env python

import json
import os


DEFAULT_CONFIG_PATH = "../etc/versioning.json"


class RepositoryManager:
    def __init__(self, repository):
        bin_dir = os.path.dirname(__file__)
        config_path = os.path.normpath(f"{bin_dir}/{DEFAULT_CONFIG_PATH}")

        with open(config_path) as config_file:
            self.configuration = json.load(config_file)
        self.repository = repository

    def get_repo_dir(self):
        path = self.configuration["repositories"][self.repository]["path"]
        full_path = None

        if path[0] == ".":
            # relative path
            # TODO: maybe don't accept this because relative path is difficult: it's relative to location of binary
            full_path = os.path.normpath(f"{os.getcwd()}/{path}")
        elif path[0] == "~":
            # path in homedir
            homedir = os.path.expanduser(path.split("/")[0])
            sub_dirs = "/".join(path.split("/")[1:])
            full_path = os.path.join(homedir, sub_dirs)

        return full_path or path


if __name__ == '__main__':
    vm = RepositoryManager("backend")
    print(f"backend: {vm.get_repo_dir()}")