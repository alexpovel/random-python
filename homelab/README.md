# Package to control aspects of the server

This project is managed using [poetry](https://python-poetry.org/).

## Setup

Setting this up for use in Visual Studio Code can be done [this way](https://github.com/microsoft/vscode-python/issues/8372#issuecomment-641816271).
Open the *Python* package root, *not* the project root in VSCode.
It will pick up the `.venv` directory automatically, if present (`poetry config virtualenvs.in-project true`).
