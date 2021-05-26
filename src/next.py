#!/usr/bin/env python

import argparse
import git
import json
import os

from lib import full_path


DEFAULT_CONFIG_PATH = "../etc/versioning.json"
DEFAULT_STAGING_BRANCH = "develop"
DEFAULT_PRODUCTION_BRANCH = "master"


class Configuration:
    """
    Entity that holds the configuration required for initialization of a `RepositoryManager`.
    """

    repo_path: str = None
    staging_branch: str = None
    production_branch: str = None

    def __init__(self, repo_path, staging_branch, production_branch):
        self.repo_path = repo_path
        self.staging_branch = staging_branch
        self.production_branch = production_branch

    def __repr__(self):
        return json.dumps({
            "repo_path": self.repo_path,
            "staging_branch": self.staging_branch,
            "production_branch": self.production_branch
        })

    @classmethod
    def config_from_file(cls, config_file_path, project_name):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on a configuration file, to use for initialization of a new `RepositoryManager`.
        """
        _bin_dir = os.path.dirname(__file__)
        _normalized_path = os.path.normpath(f"{_bin_dir}/{config_file_path}")
        with open(_normalized_path) as config_file:
            json_config = json.load(config_file)
            repo_config = json_config["projects"][project_name]

            repo_path = full_path(repo_config["path"])
            staging_branch = repo_config["branches"]["staging"]
            production_branch = repo_config["branches"]["production"]

            return Configuration(repo_path, staging_branch, production_branch)

    @classmethod
    def config_from_manual_input(cls, repo_path, staging_branch, production_branch):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on manual configuration options, to use for initialization of a new `RepositoryManager`.
        """
        return Configuration(repo_path, staging_branch, production_branch)


class RepositoryManager:
    """
    Entity through which the repository should be managed.
    """

    _configuration = None
    _repository = None

    def __init__(self, config):
        """
        Initialize a new `RepositoryManager`, based on a `RepositoryManager.Configuration`.
        """
        self._config = config
        assert self._config.repo_path
        self._repository = git.Repo(self._config.repo_path)
        assert not self._repository.bare

    @property
    def conf(self):
        """
        Get the `Configuration` object used by this `RepositoryManager`.
        """
        return self._configuration

    @property
    def repo(self):
        """
        Get the `git.Repo` object.
        """
        return self._repository


def read_version():
    with open("VERSION") as f:
        return f.read()


if __name__ == '__main__':
    # Parse arguments with argparse (https://docs.python.org/3/library/argparse.html)
    parser = argparse.ArgumentParser(
        description="Next version for next release",
        epilog="Website: https://github.com/swesterveld/next"
    )
    file_config_group = parser.add_argument_group("configuration with file")
    file_config_group.add_argument("-c", "--configuration-file", default=DEFAULT_CONFIG_PATH)
    file_config_group.add_argument("-p", "--project-name")

    # TODO: implement args for manual configuration
    # manual_config_group = parser.add_argument_group("manual configuration")
    # manual_config_group.add_argument("-r", "--repository-path")
    # manual_config_group.add_argument("-s", "--staging-branch", default=DEFAULT_STAGING_BRANCH)
    # manual_config_group.add_argument("-p", "--production-branch", default=DEFAULT_PRODUCTION_BRANCH)
    # manual_config_group.add_argument("--version", action="version", version=f"{read_version()}")

    args = parser.parse_args()

    config = Configuration.config_from_file(args.configuration_file, args.project_name)
    rm = RepositoryManager(config)

    # PoC to prove the repo could be used
    repo = rm.repo
    print(f"branches: {repo.branches}")
    print(f"heads: {repo.heads}")
