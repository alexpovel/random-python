# Psychrometric Charts (Mollier Diagram)

## Requirements

To get this party started, install Python.
*Which one?*, you ask.
*Which packages?*, you ask.
`poetry` has those answers for you in its [project configuration file](pyproject.toml).
But fear not, for you don't have to parse and process that manually.
After installing the correct Python version (listed in that file), run

```bash
python -m pip install --user poetry
```

to get the `poetry` tool installed on your system via `pip`.
Then, simply call

```bash
poetry install
```

from within the root directory.
These steps are also covered in the [CI configuration](.gitlab-ci.yml).
You can get inspiration from there.
`poetry` will then install all the requirements itself, into its own neat little virtual
environment, separate from your existing global/user Python distribution.
That's it, you're done, congratulations, wow.

### Notes

But wait, it is not that simple.
The Python package `astropy` requires a `C` compiler.
It just works on Linux.
For Windows, go [here](https://visualstudio.microsoft.com/downloads/) and
click aimlessly and install random things until it works, good luck.
