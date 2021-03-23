from importlib import import_module

from control.util.log import LOGGER

try:
    module = "docker"
    docker = import_module(module)
    _DOCKER = docker.from_env()
except ModuleNotFoundError:
    # `object()` instances don't support attribute assignment,
    # we need something more capable:
    from types import SimpleNamespace

    # Allow the script to run without the above module installed. For this to work,
    # we have fake to all currently used attributes correctly. That is pretty stupid
    # and definitely doesn't scale well, but it seemed fun.
    LOGGER.error(f"Module '{module}' not found, disabling silently.")
    _DOCKER = SimpleNamespace()
    _DOCKER.containers = SimpleNamespace()
    _DOCKER.containers.list = lambda: []


def docker_logs(container_name):
    """Fetches all available log lines (entries) from a container."""
    container = _DOCKER.containers.get(container_name)
    return [entry for entry in container.logs().decode("utf8").split("\n") if entry]
