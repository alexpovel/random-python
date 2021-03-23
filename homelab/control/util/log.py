import logging
from functools import wraps
from inspect import signature

logging.basicConfig(level=logging.DEBUG,)
LOGGER = logging.getLogger()


def log_calls(as_level):
    """Decorator to log function calls with their entire signature."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            sig = signature(f)
            binding = sig.bind(*args, **kwargs)
            LOGGER.log(
                as_level,
                "Calling: "
                + f.__module__
                + "."
                + f.__qualname__
                + " with "
                + str(binding)
            )
            res = f(*args, **kwargs)
            LOGGER.log(as_level, "Call return: " + str(res))
            return res

        return wrapper

    return decorator
