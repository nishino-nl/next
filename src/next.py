#!/usr/bin/env python

import argparse
import git
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
        full_path = path = self.configuration["repositories"][self.repository]["path"]

        # make sure to use an absolute path
        if path[0] == ".":
            # when a relative path has been given
            raise Exception("Sorry, no relative paths allowed")
        elif path[0] == "~":
            # when a path in homedir has been given
            homedir = os.path.expanduser(path.split("/")[0])
            sub_dirs = "/".join(path.split("/")[1:])
            full_path = os.path.join(homedir, sub_dirs)

        repo = git.Repo(full_path or path)
        assert not repo.bare
        return full_path

def read_version():
    with open("VERSION") as f:
        return f.read()


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser(description="Next version for next release")
    parser.add_argument("-c", "--configuration-file")
    parser.add_argument("-r", "--repository")
    parser.add_argument("-s", "--staging-branch")
    parser.add_argument("-p", "--production-branch")
    parser.add_argument("--version", action="version", version=f"{read_version()}")
    args = parser.parse_args()
    print(args)

    vm = RepositoryManager("backend")
    print(f"repo: {vm.get_repo_dir()}")  # Just to prove the repo could be used
