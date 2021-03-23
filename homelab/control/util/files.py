from pathlib import Path
from shlex import quote

from control.util.log import LOGGER
from control.util.procs import text_run

PYTHON_PACKAGE_ROOT = Path(__file__).parent.parent
LOGGER.debug(f"Python package root: {PYTHON_PACKAGE_ROOT}")

PYTHON_PROJECT_ROOT = PYTHON_PACKAGE_ROOT.parent
LOGGER.debug(f"Python project root: {PYTHON_PROJECT_ROOT}")

PROJECT_ROOT = PYTHON_PROJECT_ROOT.parent
LOGGER.debug(f"Project root: {PROJECT_ROOT}")


def strip_last_suffix(path: Path) -> Path:
    return path.with_suffix("")


def locate_executable(cmd) -> Path:
    """Returns the absolute path to the passed command, searching `$PATH`."""
    # `Path` doesn't strip trailing newline and would carry it along, so `strip`.
    return Path(text_run(["which", quote(cmd)]).stdout.strip())
