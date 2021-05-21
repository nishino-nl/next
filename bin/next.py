# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import json
import os


CONFIG_PATH = "../etc/versioning.json"


class RepositoryManager:
    def __init__(self, repository):
        with open(CONFIG_PATH) as config_file:
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
            subdirs = "/".join(path.split("/")[1:])
            full_path = os.path.join(homedir, subdirs)

        return full_path or path


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    vm = RepositoryManager("backend")
    print(f"backend: {vm.get_repo_dir()}")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
