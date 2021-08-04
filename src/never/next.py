import git
import json

from .lib import *


class Configuration:
    """
    Entity that holds the configuration required for initialization of a `RepositoryManager`.
    """

    # TODO: sort
    repo_path: str = None
    release_branch: str = None
    staging_branch: str = None
    production_branch: str = None
    version_file: str = None
    package_metadata: str = None

    def __init__(self, repo_path: str, release_branch: str, staging_branch: str, production_branch: str, version_file: str, package_metadata: str = None):
        # TODO: sort
        self.repo_path = repo_path
        self.release_branch = release_branch
        self.staging_branch = staging_branch
        self.production_branch = production_branch
        self.version_file = version_file
        self.package_metadata = package_metadata

    def __repr__(self):
        # TODO: sort
        return json.dumps({
            "repo_path": self.repo_path,
            "release_branch": self.release_branch,
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
            release_branch = repo_config["branches"]["release"]
            staging_branch = repo_config["branches"]["staging"]
            production_branch = repo_config["branches"]["production"]
            version_file = repo_config["version_file"]
            package_metadata = repo_config["package_metadata"] if "package_metadata" in repo_config else None

            return Configuration(repo_path, release_branch, staging_branch, production_branch, version_file, package_metadata)

    @classmethod
    def config_from_manual_input(cls, repo_path, release_branch, staging_branch, production_branch, version_file, package_metadata = None):
        """
        Provide a valid `RepositoryManager.Configuration` object, based on manual configuration options, to use for initialization of a new `RepositoryManager`.
        """
        return Configuration(repo_path, release_branch, staging_branch, production_branch, version_file, package_metadata)


class RepositoryManager:
    """
    Entity through which the repository should be managed.
    """

    _configuration = None
    _prior_branch = None
    _repository = None
    _version: tuple = None

    _to_stage: list = []

    def __init__(self, config):
        """
        Initialize a new `RepositoryManager`, based on a `RepositoryManager.Configuration` and the current state.
        """
        self._configuration = config
        assert self._configuration.repo_path
        self._repository = git.Repo(self._configuration.repo_path)
        assert not self._repository.bare

        self._version = self.get_version()
        self._prior_branch = self.repo.active_branch

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
    def bump_version(self, bump_level: VersionLevel) -> tuple:
        """
        Bump version based on a given level.

        The `VERSION` file will be updated with bumped version (and committed to current branch).

        :param bump_level: the VersionLevel (IntEnum) to bump.
        :return: version after the bump has taken place.
        """
        original_version = self.version
        new_version = determine_next_version(self.version, bump_level)

        # store new version in VERSION-file (as single source of truth)
        self.store_version(new_version)

        # if VERSION needs to be updated in other files (like `package.json`) as well, do it here
        if self.conf.package_metadata:
            # TODO: support multiple metadata filetypes (currently only working for package.json files)
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

        # stage, commit and push VERSION file to current branch
        _index = self.repo.index
        _index.add(self.staged)
        _index.commit(f"automated {VersionLevel(bump_level).name.lower()}-level version bump from {version_tpl_to_str(original_version)} to {version_tpl_to_str(new_version)}")

        return new_version

    def release(self, bump_level: VersionLevel, environment: Environment = Environment.DEVELOPMENT) -> tuple:
        """
        Tag latest commit on the staging-branch with a version based on the given bump-level.
        """
        assert self.origin.exists() # TODO: error-handling

        # make sure repo is clean
        self.verify_repo_clean() # TODO: include error-handling

        # check out branches for staging and production and make sure their HEADs are up-to-date
        prior_branch = self.repo.active_branch
        self.update_head(self.staging)
        self.update_head(self.production)
        prior_branch.checkout()

        # determine next version
        next_version = determine_next_version(self.version, bump_level)

        # check release strategy (separate branch, or just version-tag-commit)
        if self.conf.release_branch:
            branch_name = self.prepare_release_branch(next_version)
            print(f"releasing to dedicated release-branch: {branch_name}")
        else:
            print(f"releasing to existing branch: {self.repo.active_branch}")

        # bump version and push to origin
        bumped_version = self.bump_version(bump_level)
        bumped_version_str = version_tpl_to_str(bumped_version)
        new_tag = self.repo.create_tag(f"v{bumped_version_str}")

        self.origin.push(new_tag)
        self.origin.push(refspec=f"{branch_name}:{branch_name}")

        # return to branch where we originally started from
        if self._prior_branch:
            self.repo.git.checkout(self._prior_branch)
        # print(f"bumped to version: {bumped_version}")
        return bumped_version

    def prepare_release_branch(self, new_version: tuple):
        """
        Create dedicated release branch, based on new version.
        """
        # TODO: first make sure we're on develop
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