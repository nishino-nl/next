# next
Next version for next release

## how to use

Setup an environment with the dependencies once, if you haven't done that yet.

```shell
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ python src/next.py -h
usage: next.py [-h] [--settings | --no-settings] [--version] [-f SETTINGS_FILE] [-p PROJECT] {major,minor,patch}

Next version for next release

positional arguments:
  {major,minor,patch}

optional arguments:
  -h, --help            show this help message and exit
  --settings, --no-settings
                        whether to use a settings-file for your configuration, or provide the settings manually
  --version             show program's version number and exit

required when using a settings-file for your configuration:
  -f SETTINGS_FILE, --settings-file SETTINGS_FILE
  -p PROJECT, --project PROJECT

Website: https://github.com/swesterveld/next
```

## dependencies

This project has some dependencies mentioned in the `requirements.txt` file.
Documentation of these Python packages could be found at:
* [GitPython](https://gitpython.readthedocs.io/en/stable/)

Other dependencies, from the Python Standard Library, are documented here:
* [argparse](https://docs.python.org/3/library/argparse.html)