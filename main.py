#!/usr/bin/env python

# Just a useful example of how to use the example_pkg package

from src.example_pkg.lib import version_tpl_to_str
from src.example_pkg.next import Configuration, RepositoryManager, VersionLevel, read_version, DEFAULT_SETTINGS_PATH

import argparse

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

    # release bumped version
    new_version = rm.release(args.bump_level)

    # checkout production-branch and merge staging-branch into it
    rm.prepare_production()

    # TODO: implement deploy
    print(f"Released version {version_tpl_to_str(new_version)}. Ready to deploy...")