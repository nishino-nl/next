import git
import json

from enum import Enum

from .lib import *

DEFAULT_STAGING_BRANCH = "develop"
DEFAULT_PRODUCTION_BRANCH = "master"


class VersionLevel(Enum):
    MAJOR = 0
    MINOR = 1
    PATCH = 2

    def __str__(self):
        return self.name.lower()


class Environment(Enum):
    DEVELOPMENT = 0
    PRODUCTION = 1


class Configuration:
    """
    Entity that holds the configuration required for initialization of a `RepositoryManager`.
    """

    repo_path: str = None
    staging_branch: str = None
    production_branch: str = None
    version_file: str = None
    package_metadata: str = None

    def __init__(self, repo_path: str, staging_branch: str, production_branch: str, version_file: str, package_metadata: str = None):
        self.repo_path = repo_path
        self.staging_branch = staging_branch
        self.production_branch = production_branch
        self.version_file = version_file
        self.package_metadata = package_metadata

    def __repr__(self):
        return json.dumps({
            "repo_path": self.repo_path,
            "staging_branch": self.staging_branch,
            "production_branch": self.production_branch,
            "version_file": self.version_file,
            "package_metadata": self.package_metadata or None,
        })

    @classmethod
    def config_from_file(cls, config_file_path, project):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on a configuration file, to use for initialization of a new `RepositoryManager`.
        """
        _cwd = os.getcwd()
        _normalized_path = os.path.normpath(f"{_cwd}/{config_file_path}")
        with open(_normalized_path) as config_file:
            json_config = json.load(config_file)
            repo_config = json_config["projects"][project]

            repo_path = full_path(repo_config["path"])
            staging_branch = repo_config["branches"]["staging"]
            production_branch = repo_config["branches"]["production"]
            version_file = repo_config["version_file"]
            package_metadata = repo_config["package_metadata"] if "package_metadata" in repo_config else None

            return Configuration(repo_path, staging_branch, production_branch, version_file, package_metadata)

    @classmethod
    def config_from_manual_input(cls, repo_path, staging_branch, production_branch, version_file, package_metadata = None):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on manual configuration options, to use for initialization of a new `RepositoryManager`.
        """
        return Configuration(repo_path, staging_branch, production_branch, version_file, package_metadata)


class RepositoryManager:
    """
    Entity through which the repository should be managed.
    """

    _configuration = None
    _repository = None
    _version: tuple = None

    _to_stage: list = []

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

    @property
    def origin(self):
        return self.repo.remotes.origin

    @property
    def production(self):
        return self.repo.heads[self.conf.production_branch]

    @property
    def staging(self):
        return self.repo.heads[self.conf.staging_branch]

    def stage(self, file_path):
        self._to_stage.append(file_path)
        self._to_stage = list(set(self._to_stage))

    @property
    def staged(self):
        return self._to_stage

    def get_version(self) -> tuple:
        """
        Get version number from the VERSION file in the repository.
        """
        _version_file = os.path.normpath(f"{self.conf.repo_path}/{self.conf.version_file}")
        return read_version(_version_file)

    def store_version(self, version: tuple):
        """
        Store version number to internal state and to the VERSION file in the repository.

        :param version: the version to store.
        """
        _version_file = os.path.normpath(f"{self.conf.repo_path}/{self.conf.version_file}")
        write_version(version, _version_file)
        self.stage(_version_file)
        self._version = version

    @property
    def version(self) -> tuple:
        return self._version

    # TODO: maybe refactor `bump_version()` to `release_next(level: {major,minor,patch})`
    def bump_version(self, bump_level: int) -> tuple:
        """
        Bump version based on a given level.

        The `VERSION` file will be updated with bumped version (and committed to staging-branch).

        :param bump_level: one of `major`, `minor` or `patch`.
        :return: version after the bump has taken place.
        """
        major, minor, patch = original_version = self.version

        # define new version based on current version and bump-level (major|minor|patch)
        new_version = (
            major + 1 if bump_level is VersionLevel.MAJOR.value
            else major,
            minor + 1 if bump_level is VersionLevel.MINOR.value
            else 0 if bump_level < VersionLevel.MINOR.value
            else minor,
            patch + 1 if bump_level is VersionLevel.PATCH.value
            else 0,
        )

        # switch to staging branch, to start version bumping
        self.staging.checkout()

        # store new version in VERSION-file (as single source of truth)
        self.store_version(new_version)

        # if VERSION needs to be updated in other files (like `package.json`) as well, do it here
        if self.conf.package_metadata:
            # update package metadata
            print(f"update metadata in {self.conf.package_metadata}")
            _metadata_path = os.path.normpath(f"{self.conf.repo_path}/{self.conf.package_metadata}")

            with open(_metadata_path, "r+") as metadata_file:
                metadata = json.load(metadata_file)
                print(f"current version: {metadata['version']}")
                metadata["version"] = version_tpl_to_str(new_version)

                # overwrite contents of metadata file with updated metadata
                metadata_file.seek(0)
                json.dump(metadata, metadata_file, indent=2)
                metadata_file.truncate()
                self.stage(_metadata_path)

        # stage, commit and push VERSION file to staging-branch
        _index = self.repo.index
        _index.add(self.staged)
        _index.commit(f"automated {VersionLevel(bump_level).name.lower()}-level version bump from {version_tpl_to_str(original_version)} to {version_tpl_to_str(new_version)}")
        self.origin.push()

        return new_version

    def release(self, bump_level: VersionLevel, environment: Environment = Environment.DEVELOPMENT) -> tuple:
        """
        Tag latest commit on the staging-branch with a version based on the given bump-level.
        """
        assert self.origin.exists()

        # make sure repo is clean
        self.verify_repo_clean()

        # check out branches for staging and master and make sure their HEADs are up-to-date
        prior_branch = self.repo.active_branch
        self.update_head(self.staging)
        self.update_head(self.production)

        # bump version and push to origin
        bumped_version = self.bump_version(VersionLevel[bump_level.upper()].value)
        bumped_version_str = version_tpl_to_str(bumped_version)
        new_tag = self.repo.create_tag(f"v{bumped_version_str}")
        self.origin.push(new_tag)
        self.origin.push()

        # return to branch where we originally started from
        self.repo.git.checkout(prior_branch)
        return bumped_version

    def prepare_production(self):
        """
        Merge staging-branch into production-branch to prepare for deployment to production.
        """
        self.staging.checkout()
        self.repo.git.merge(self.production)
        self.origin.push()

        self.production.checkout()
        self.repo.git.merge(self.staging)
        self.origin.push()

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

        self.origin.fetch()
        self.origin.pull()