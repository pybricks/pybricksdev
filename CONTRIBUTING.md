# Contributing to pybricksdev

`pybricksdev` is open source software and we welcome contributions.


## Developer environment

This is the preferred workflow that we support. If you have other tools you like
to use, you are welcome to use them, but we can't help you if things go wrong.

### Prerequisites

- [Git](https://git-scm.com/) (or install `git` with your favorite package manager)
- [Python](https://python.org) (see [README](./README.md) for more info)
- [Poetry](https://python-poetry.org/)
- [VS Code](https://code.visualstudio.com/)

### Get the code and setup the environment

After installing the prerequisites, use a command prompt in the location of your
choice to run the following:

    git clone https://github.com/pybricks/pybricksdev
    cd pybricksdev
    poetry env use python3.12
    poetry install
    code .

On Windows, you may need to use the full path to `python3.12` (run `py -0p` to find it).

You will need to tell VS Code to use `.venv` as the Python interpreter. It
should ask you about this the first time you open the project folder.

You should also opt into the [DeprecatePythonPath] experiment for the Microsoft
Python VS Code extension so that it does not modify the `.vscode/settings.json`
file in the project when you select the interpreter.

[DeprecatePythonPath]: https://github.com/microsoft/vscode-python/wiki/AB-Experiments#deprecatepythonpath

### Test your changes

#### Run a script on your Hub

    poetry run pybricksdev run ble test.py

#### Build and install your changes globally

    poetry build
    pipx install --force ./dist/pybricksdev-1.0.0a19.tar.gz

#### Inject a custom dependency

For instance, if you want the installed `pybricksdev` to use code from the `develop` branch of the `bleak` package.

    pipx inject pybricksdev https://github.com/hbldh/bleak/archive/refs/heads/develop.zip
