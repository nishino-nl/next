#!/usr/bin/env python

import argparse
import git
import json

from enum import Enum

from lib import *

DEFAULT_SETTINGS_PATH = "../etc/versioning.json"
DEFAULT_STAGING_BRANCH = "develop"
DEFAULT_PRODUCTION_BRANCH = "master"


class VersionLevel(Enum):
    MAJOR = 0
    MINOR = 1
    PATCH = 2

    def __str__(self):
        return self.name.lower()


class Configuration:
    """
    Entity that holds the configuration required for initialization of a `RepositoryManager`.
    """

    repo_path: str = None
    staging_branch: str = None
    production_branch: str = None
    version_file: str = None

    def __init__(self, repo_path, staging_branch, production_branch, version_file):
        self.repo_path = repo_path
        self.staging_branch = staging_branch
        self.production_branch = production_branch
        self.version_file = version_file

    def __repr__(self):
        return json.dumps({
            "repo_path": self.repo_path,
            "staging_branch": self.staging_branch,
            "production_branch": self.production_branch,
            "version_file": self.version_file
        })

    @classmethod
    def config_from_file(cls, config_file_path, project):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on a configuration file, to use for initialization of a new `RepositoryManager`.
        """
        _bin_dir = os.path.dirname(__file__)
        _normalized_path = os.path.normpath(f"{_bin_dir}/{config_file_path}")
        with open(_normalized_path) as config_file:
            json_config = json.load(config_file)
            repo_config = json_config["projects"][project]

            repo_path = full_path(repo_config["path"])
            staging_branch = repo_config["branches"]["staging"]
            production_branch = repo_config["branches"]["production"]
            version_file = repo_config["version_file"]

            return Configuration(repo_path, staging_branch, production_branch, version_file)

    @classmethod
    def config_from_manual_input(cls, repo_path, staging_branch, production_branch, version_file):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on manual configuration options, to use for initialization of a new `RepositoryManager`.
        """
        return Configuration(repo_path, staging_branch, production_branch, version_file)


class RepositoryManager:
    """
    Entity through which the repository should be managed.
    """

    _configuration = None
    _repository = None
    _version: tuple = None

    def __init__(self, config):
        """
        Initialize a new `RepositoryManager`, based on a `RepositoryManager.Configuration`.
        """
        self._configuration = config
        assert self._configuration.repo_path
        self._repository = git.Repo(self._configuration.repo_path)
        assert not self._repository.bare
        self._version = self.get_version()

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

    def get_version(self) -> tuple:
        """
        Get version number from the VERSION file in the repository.
        """
        _version_file = os.path.normpath(f"{self.conf.repo_path}/{self.conf.version_file}")
        return read_version(_version_file)

    def store_version(self, version: tuple):
        """
        Store version number to internal state and to the VERSION file in the repository

        :param version: the version to store.
        """
        _version_file = os.path.normpath(f"{self.conf.repo_path}/{self.conf.version_file}")
        write_version(version, _version_file)
        self._version = version

    @property
    def version(self) -> tuple:
        return self._version

    def bump_version(self, level: int) -> tuple:
        """
        Bump version based on a given level.

        :param level: one of `major`, `minor` or `patch`.
        :return: version after the bump has taken place.
        """
        major, minor, patch = self.version

        new_version = (
            major + 1 if level is VersionLevel.MAJOR.value
            else major,
            minor + 1 if level is VersionLevel.MINOR.value
            else 0 if level < VersionLevel.MINOR.value
            else minor,
            patch + 1 if level is VersionLevel.PATCH.value
            else 0,
        )

        self.store_version(new_version)
        return new_version

    def release(self):
        # TODO: implement bump + commit + push on develop
        pass

    def prepare_production(self):
        # TODO: implement merge + push on master
        pass

    def verify_repo_clean(self):
        # make sure repo is clean
        changes_to_be_committed = index.diff(repo.head.commit)
        try:
            assert changes_to_be_committed == []
        except AssertionError:
            print("There are still changes to be committed. Either commit or unstage and discard them first.")
            exit(1)

        changes_not_staged = index.diff(None)
        try:
            assert changes_not_staged == []
        except AssertionError:
            print("There are still changes not staged for commit. Either commit or discard them first")
            exit(1)


if __name__ == '__main__':
    # Parse arguments with argparse (https://docs.python.org/3/library/argparse.html)
    parser = argparse.ArgumentParser(
        description="Next version for next release",
        epilog="Website: https://github.com/swesterveld/next"
    )
    parser.add_argument("bump_level", choices=[
        str(VersionLevel(level)) for level in VersionLevel
    ])
    parser.add_argument("--settings", action=argparse.BooleanOptionalAction, help="whether to use a settings-file for your configuration, or provide the settings manually")
    parser.add_argument("--version", action="version", version=f"{read_version('VERSION')}")

    file_config_group = parser.add_argument_group("required when using a settings-file for your configuration")
    file_config_group.add_argument("-f", "--settings-file", default=DEFAULT_SETTINGS_PATH)
    file_config_group.add_argument("-p", "--project")

    # TODO: implement args for manual configuration
    # manual_config_group = parser.add_argument_group("manual configuration")
    # manual_config_group.add_argument("-r", "--repository-path")
    # manual_config_group.add_argument("-s", "--staging-branch", default=DEFAULT_STAGING_BRANCH)
    # manual_config_group.add_argument("-p", "--production-branch", default=DEFAULT_PRODUCTION_BRANCH)
    # manual_config_group.add_argument("--version", action="version", version=f"{read_version()}")

    args = parser.parse_args()

    # bail out when --settings has been set without providing its required arguments --settings-file and --project
    if args.settings and not (args.settings_file and args.project):
        print(f"Exiting because both --settings-file and --project are required when using a settings-file for your configuration\n")
        parser.print_help()
        exit(1)

    # bump version for project in configuration
    config = Configuration.config_from_file(args.settings_file, args.project)
    rm = RepositoryManager(config)
    current_version_str = version_tpl_to_str(rm.version)

    repo = rm.repo
    staging = repo.heads[rm.conf.staging_branch]
    production = repo.heads[rm.conf.production_branch]
    index = repo.index

    origin = repo.remotes.origin
    assert origin.exists()

    rm.verify_repo_clean()

    # check out branches for staging and master and make sure their HEADs are up-to-date
    prior_branch = repo.active_branch

    staging.checkout()
    print(f"current branch: {repo.active_branch}")
    origin.fetch()
    origin.pull()

    production.checkout()
    print(f"current branch: {repo.active_branch}")
    origin.fetch()
    origin.pull()

    # checkout develop
    staging.checkout()

    # bump version
    bumped_version_str = version_tpl_to_str(rm.bump_version(VersionLevel[args.bump_level.upper()].value))

    # stage, commit and push VERSION file to staging-branch
    index.add([rm.conf.version_file])
    index.commit(f"automated {args.bump_level}-version bump from {current_version_str} to {bumped_version_str}")
    origin.push()

    # tag latest commit with bumped version and push it to staging-branch
    new_tag = repo.create_tag(f"v{bumped_version_str}")
    origin.push(new_tag)

    # checkout production-branch and merge staging-branch into it
    production.checkout()
    repo.git.merge(staging)

    # push production-branch
    origin.push()

    # TODO: return to branch where we originally started from
    repo.git.checkout(prior_branch)
    print(f"current branch: {repo.active_branch}")

    # TODO: implement deploy
    print(f"Released version {bumped_version_str}. Ready to deploy...")