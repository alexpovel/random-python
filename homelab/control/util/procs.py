import time
from datetime import datetime as dt
from datetime import timedelta as td
from functools import wraps
from subprocess import CalledProcessError, run

from control.util.log import LOGGER


def text_run(cmd, **kwargs):
    try:
        return run(cmd, check=True, capture_output=True, text=True, **kwargs)
    except CalledProcessError as e:
        LOGGER.error(e.stderr)
        raise CalledTextProcessError(**vars(e))


class CalledTextProcessError(CalledProcessError):
    """Parent class does not print stdout and stderr by default, do that here.

    If capturing command output and the output's text, this is very convenient.
    """

    def __str__(self):
        return (
            f"Command '{self.cmd}' returned exit status {self.returncode}, with"
            f" output='{self.output}' and stderr='{self.stderr}'."
        )


class DnsResolutionError(CalledTextProcessError):
    """Raised if a process fails because of DNS resolution errors."""

    pass


def retry(
    on_exception: Exception, timeout=td(seconds=120), backoff=td(seconds=1),
):
    """Calls the decorated function repeatedly, with increasingly longer breaks.

    Args:
        on_exception: Only retry if this exception is raised.
        timeout: Maximum duration to wait before aborting.
        backoff: Initial duration to wait after the first failed attempt, after which
            this duration increases exponentially between further attempts.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal backoff
            start = dt.now()
            LOGGER.debug("Starting function call retries.")
            n = 1
            while True:
                LOGGER.info(f"Running try number {n}.")
                try:
                    res = func(*args, **kwargs)
                    LOGGER.info("Call succeeded.")
                    return res
                except on_exception:
                    LOGGER.warning(f"Call failed (raised {on_exception}).")
                    n += 1
                    now = dt.now()
                    delta = now - start
                    if delta > timeout:
                        LOGGER.error("Timeout reached, exiting.")
                        raise
                    LOGGER.info(f"Sleeping for {backoff}.")
                    time.sleep(backoff.total_seconds())
                    backoff *= 2  # exponential

        return wrapper

    return decorator
