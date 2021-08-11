# ne-ver - Next Version
Ne-ver again the manual hassle to release a next version.


## how to use

Setup an environment with the dependencies once, if you haven't done that yet.

```commandline
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install ne-ver
$ never -h
usage: never [-h] [--settings | --no-settings] [-f SETTINGS_FILE] [-p PROJECT] {major,minor,patch}

Ne-ver again the manual hassle to release a next version

positional arguments:
  {major,minor,patch}

optional arguments:
  -h, --help            show this help message and exit
  --settings, --no-settings
                        whether to use a settings-file for your configuration, or provide the settings manually

required when using a settings-file for your configuration:
  -f SETTINGS_FILE, --settings-file SETTINGS_FILE
  -p PROJECT, --project PROJECT

Website: https://github.com/swesterveld/next
```


### GitHub token

A GitHub token is required to let `never` create pull requests for you.
Make sure to generate a personal access token in [your GitHub Developer Settings](https://github.com/settings/tokens),
with at least the scope `repo` -- for full control of private repositories -- selected.

Add this token to the `.env` file at the root of your virtualenv.
The `.env` file should be based on the `.env.example` file in the `examples` directory.
Make sure to reload the virtualenv to activate the environment variable(s) defined in the `.env` file.


### settings

Currently, the `--no-settings` flag doesn't work yet, so you should use a settings file.
The settings file should be JSON-formatted. Its contents should be like:

```json
{
  "projects": {
    "backend": {
      "path": "~/repos/some-repo-clone-of-backend-project",
      "branches": {
        "release": "release/{version}",
        "staging": "develop",
        "production": "master"
      },
      "version_file": "VERSION"
    },
    "frontend": {
      "path": "/home/jdoe/repos/some-repo-clone-of-frontend-project",
      "branches": {
        "release": "release/{version}",
        "staging": "develop",
        "production": "master"
      },
      "version_file": "VERSION",
      "package_metadata": "package.json"
    }
  }
}
```


### run

An example, to bump the version from `x.y.z` to `x.y.z+1` for project `frontend` defined in `etc/never.config.json`:

```commandline
never patch --settings -f etc/never.config.json -p frontend
```


## development

### run in development mode
You could benefit from the option to [run `setuptools` in development mode](https://setuptools.readthedocs.io/en/latest/userguide/quickstart.html#development-mode),
which allows you to modify the source code and have the changes take effect without you having to rebuild and reinstall:

```commandline
pip install  --editable .
```

### build Python package
As a prerequisite for building a Python package you'll need a builder, such as [PyPA build](https://pypa-build.readthedocs.io/en/latest/index.html).
If you haven't got a builder yet, you can obtain it via `pip install build`.

To invoke the builder:

```commandline
python -m build
```


### release to PyPI

```commandline
python -m twine upload --repository pypi dist/*
```


## dependencies

This project has some dependencies mentioned in the `requirements.txt` file.
Documentation of these Python packages could be found at:
* [GitPython](https://gitpython.readthedocs.io/en/stable/)
* [python-dotenv](https://saurabh-kumar.com/python-dotenv/)
* [Requests](https://docs.python-requests.org/en/master/)

Other dependencies, from the Python Standard Library, are documented here:
* [argparse](https://docs.python.org/3/library/argparse.html)