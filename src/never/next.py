import configparser

import git
import json
import os
import re
import requests

from .lib import *


class Configuration:  # TODO: separate module
    """
    Entity that holds the configuration required for initialization of a `RepositoryManager`.
    """

    def __init__(self, repo_path: str, production_branch: str, release_branch: str, staging_branch: str,
                 package_metadata: str = None, version_file: str = DEFAULT_VERION_FILE):
        # project path
        self.repo_path: str = repo_path
        # branches
        self.production_branch: str = production_branch
        self.release_branch: str = release_branch
        self.staging_branch: str = staging_branch
        # package data
        self.package_metadata: str = package_metadata
        self.version_file: str = version_file

    def __repr__(self):
        return json.dumps({
            # project path
            "repo_path": self.repo_path,
            # branches
            "production_branch": self.production_branch,
            "release_branch": self.release_branch,
            "staging_branch": self.staging_branch,
            # package data
            "package_metadata": self.package_metadata,
            "version_file": self.version_file,
        })

    @classmethod
    def config_from_file(cls, config_file_path, project):
        """
        Provide a valid `Configuration` object, based on a configuration file, to use for initialization of a new `RepositoryManager`.
        """
        _cwd = os.getcwd()
        _normalized_path = os.path.normpath(f"{_cwd}/{config_file_path}")
        with open(_normalized_path) as config_file:
            json_config = json.load(config_file)
            repo_config = json_config["projects"][project]

            # project path
            repo_path = full_path(repo_config["path"])
            # branches
            production_branch = repo_config["branches"]["production"]
            release_branch = repo_config["branches"]["release"]
            staging_branch = repo_config["branches"]["staging"]
            # package data
            package_metadata = repo_config["package_metadata"] if "package_metadata" in repo_config else None
            version_file = repo_config["version_file"]

            return Configuration(repo_path, production_branch, release_branch, staging_branch, package_metadata, version_file)

    @classmethod
    def config_from_manual_input(cls, repo_path, production_branch, release_branch, staging_branch,
                                 package_metadata = None, version_file = DEFAULT_VERION_FILE):
        """
        Provide a valid `Configuration` object, based on manual configuration options, to use for initialization of a new `RepositoryManager`.
        """
        return Configuration(repo_path, production_branch, release_branch, staging_branch, package_metadata, version_file)


class RepositoryManager:
    """
    Entity through which the repository should be managed.
    It keeps track of the repository's state, and could help to change its state in a controlled manner.
    """

    def __init__(self, config: Configuration, *args, **kwargs):
        """
        Initialize a new `RepositoryManager`, based on a `Configuration` and the current state.
        """
        self._configuration: Configuration = config
        assert self._configuration.repo_path
        self._repository = git.Repo(self._configuration.repo_path)
        assert not self._repository.bare

        self._prior_branch = self.repo.active_branch
        self._to_stage: list = []
        self._version: tuple = None

    @property
    def conf(self):
        """
        Get the `Configuration` object used by this `RepositoryManager`.
        """
        return self._configuration

    @property
    def index(self):
        """
        Get the index (staged files)
        """
        return self.repo.index

    @property
    def repo(self):
        """
        Get the `git.Repo` object.
        """
        return self._repository

    @property
    def origin(self):
        return self.repo.remotes.origin

    @property
    def remote_url(self):
        return self.repo.remotes.origin.url
        # return [url for url in self.repo.remotes[0].urls][0]

    @property
    def remote_info(self):
        """
        Parse info about the remote from its URL.
        At GitHub, remote URL's could be formatted like:

            1. "git@github.com:<repo_owner>/<repo_name>.git"
            2. "https://github.com/<repo_owner>/<repo_name>.git"

        :return: dictionary with URL, repo owner and repo name
        """
        repo_owner, repo_name = re.split(r"[/:.]", self.remote_url)[-3:-1]
        info = {
            "url": self.remote_url,
            "repo_owner": repo_owner,
            "repo_name": repo_name
        }
        return info

    @property
    def production(self):
        return self.repo.heads[self.conf.production_branch]

    @property
    def staging(self):
        return self.repo.heads[self.conf.staging_branch]

    def mark_to_stage(self, file_path):
        self._to_stage.append(file_path)
        self._to_stage = list(set(self._to_stage))

    @property
    def marked_to_stage(self):
        return self._to_stage

    def prepare_release_branch(self, new_version: tuple):
        """
        Create dedicated release branch, based on new version.
        """
        # TODO: first make sure we're on develop
        print(f"{self.repo.active_branch} ({type(self.repo.active_branch)})")
        self.staging.checkout()

        # branch_name = f"release/v{version_tpl_to_str(new_version)}"
        new_version_str = version_tpl_to_str(new_version)
        branch_name = self.conf.release_branch.format(version=new_version_str)

        # Could raise an OSError("Reference at %r does already exist, pointing to %r, requested was %r")
        release_branch = self.repo.create_head(branch_name)
        self.repo.head.reference = release_branch
        assert not self.repo.head.is_detached
        # self.repo.head.reset(index=True, working_tree=True)
        return branch_name

    # def prepare_production(self):
    #     """
    #     Merge staging-branch into production-branch to prepare for deployment to production.
    #     """
    #     self.staging.checkout()
    #     self.repo.git.merge(self.production)
    #     self.origin.push()
    #
    #     self.production.checkout()
    #     self.repo.git.merge(self.staging)
    #     self.origin.push()

    def stage_commit_tag_push(self, original_version: tuple, new_version: tuple, bump_level: VersionLevel) -> None:
        """
        Stage and commit files marked to stage, add tag and push.
        """
        branch_name = self.repo.active_branch

        # stage, commit and push VERSION file to current branch
        self.index.add(self.marked_to_stage)

        bump_level_str = VersionLevel(bump_level).name.lower()
        original_version_str = version_tpl_to_str(original_version)
        new_version_str = version_tpl_to_str(new_version)
        commit_msg = f"automated {bump_level_str}-level version bump from {original_version_str} to {new_version_str}"
        self.index.commit(commit_msg)

        self.tag_version(new_version)
        self.origin.push(refspec=f"{branch_name}:{branch_name}")


    def tag_version(self, version: tuple) -> None:
        """
        Tag current HEAD with given version.

        :param version: the version to use for the tag
        """
        tag_str = f"v{version_tpl_to_str(version)}"
        new_tag = self.repo.create_tag(tag_str)
        self.origin.push(new_tag)
        print(f"added tag: {new_tag}")

    def verify_repo_clean(self) -> None:
        """
        Check for any local changes on the active branch.
        """
        index = self.repo.index
        changes_to_be_committed = index.diff(self.repo.head.commit)
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

    def update_head(self, head=None):
        """
        Update HEAD to branch tip on remote
        """
        if head is not None:
            head.checkout()

        self.origin.pull()

    def create_pull_request(self, title, description, head_branch, base_branch):
        """
        Creates a Pull Request for the `head_branch` against the `base_branch`, based on these GitHub docs:

        https://docs.github.com/en/rest/reference/pulls#create-a-pull-request

        :param title: The title for the new Pull Request.
        :param description: The contents of the Pull Request.
        :param head_branch: The name of the branch where your changes are implemented.
        :param base_branch: The name of the branch you want the changes pulled into.
        """
        git_pulls_api = f"https://api.github.com/repos/{self.remote_info['repo_owner']}/{self.remote_info['repo_name']}/pulls"
        git_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {git_token}",
            "Content-Type": "application/json",
            "User-Agent": "ne-ver"
        }
        payload = {
            "title": title,
            "body": description,
            "head": head_branch,
            "base": base_branch,
        }

        response = requests.post(
            git_pulls_api,
            headers=headers,
            data=json.dumps(payload),
        )

        if not response.ok:
            print("Request Failed: {0}".format(response.text))
        else:
            text = json.loads(response.text)
            print(f"Created Pull Request at {text.get('html_url')}")

            # TODO: Also add a label to the PR (issue) to mark it for automatic merging


class ReleaseManager:
    """
    Entity in control of releasing next version.
    """

    def __init__(self, configuration: Configuration, repository: RepositoryManager, bump_level: VersionLevel):
        self._bump_level: VersionLevel = bump_level
        self._configuration: Configuration = configuration
        self._repository: RepositoryManager = repository

        self._current_version = self.get_version()
        self._next_version = determine_next_version(self._current_version, bump_level)

    def bump_version(self) -> tuple:
        """
        Bump version to the next version, based on current version and bump-level.

        The `VERSION` file will be updated with bumped version (and staged to the index).
        """
        # store next version in VERSION-file (as single source of truth)
        new_version = self.store_version(self.next_version)

        # if VERSION needs to be updated in other files (like `package.json`) as well, also do that here
        if self.conf.package_metadata:
            # TODO: support multiple metadata filetypes (currently only working for package.json files)
            # update package metadata
            print(f"update metadata in {self.conf.package_metadata}")
            _metadata_path = os.path.normpath(f"{self.conf.repo_path}/{self.conf.package_metadata}")

            with open(_metadata_path, "r+") as metadata_file:
                if self.conf.package_metadata == "package.json":
                    metadata = json.load(metadata_file)
                    # print(f"current version: {metadata['version']}")
                    metadata["version"] = version_tpl_to_str(new_version)

                    # overwrite contents of metadata file with updated metadata
                    metadata_file.seek(0)
                    json.dump(metadata, metadata_file, indent=2)
                    metadata_file.truncate()

                if self.conf.package_metadata == "setup.cfg":
                    parser = configparser.ConfigParser()
                    parser.read(_metadata_path)
                    parser["metadata"]["version"] = version_tpl_to_str(new_version)
                    parser.write(metadata_file)

            self._repository.mark_to_stage(_metadata_path)

        return new_version

    @property
    def conf(self):
        """
        Get the `Configuration` object used by this `RepositoryManager`.
        """
        return self._configuration

    def get_version(self) -> tuple:
        """
        Get version number from the VERSION file in the repository.
        """
        _version_file = os.path.normpath(f"{self.conf.repo_path}/{self.conf.version_file}")
        return read_version(_version_file)

    @property
    def next_version(self) -> tuple:
        if self.version is self._next_version or self._next_version is None:
            self._next_version = determine_next_version(self.version, self._bump_level)
        return self._next_version

    def store_version(self, version: tuple):
        """
        Store version number to internal state and to the VERSION file in the repository.

        :param version: the version to store.
        """
        _version_file = os.path.normpath(f"{self.conf.repo_path}/{self.conf.version_file}")
        write_version(version, _version_file)
        self._repository.mark_to_stage(_version_file)
        self._current_version = version
        return version

    @property
    def version(self) -> tuple:
        return self._current_version

    def release(self, bump_level: VersionLevel) -> tuple:
        new_version = self.prepare_release(bump_level)

        self._repository.create_pull_request(
            f"Release {version_tpl_to_str(new_version)}",
            f"Automated {VersionLevel(bump_level).name.lower()}-level version bump to {version_tpl_to_str(new_version)}",
            f"release/{version_tpl_to_str(new_version)}",
            self._repository.staging.name,
        )

        return new_version

    def prepare_release(self, bump_level: VersionLevel, environment: Environment = Environment.DEVELOPMENT) -> tuple:
        """
        Release new version, based on current version and bump-level; bump version, commit, tag and push.
        """
        assert self._repository.origin.exists() # TODO: error-handling

        # make sure repo is clean
        self._repository.verify_repo_clean() # TODO: include error-handling

        # check out branches for staging and production and make sure their HEADs are up-to-date
        prior_branch = self._repository.repo.active_branch
        self._repository.update_head(self._repository.staging)
        self._repository.update_head(self._repository.production)
        prior_branch.checkout()

        original_version = self.version

        # check release strategy (separate branch, or just version-tag-commit)
        if self.conf.release_branch:
            branch_name = self._repository.prepare_release_branch(self.next_version)
            print(f"releasing to dedicated release-branch: {branch_name}")
        else:
            print(f"releasing to existing branch: {self._repository.repo.active_branch}")

        # bump version, commit, tag and push to origin
        new_version = self.bump_version()
        self._repository.stage_commit_tag_push(original_version, new_version, bump_level)

        # return to branch where we originally started from
        if self._repository._prior_branch:
            self._repository.repo.git.checkout(self._repository._prior_branch)
        return new_version