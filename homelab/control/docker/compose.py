"""There exists no official docker-compose Python library, see also
https://github.com/docker/compose/issues/4542.
"""

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from re import compile
from shlex import split
from subprocess import CalledProcessError, CompletedProcess
from textwrap import dedent
from typing import Callable, List

import yaml  # Already present if docker-compose is installed
from control.docker import _DOCKER
from control.util.log import LOGGER, log_calls
from control.util.misc import sorted_reverse
from control.util.procs import CalledTextProcessError, DnsResolutionError, retry, text_run


@dataclass
class CommandMetadata:
    """Holds metadata to a command."""

    desc: str  # Simple command description
    order: Callable  # Ordering should *multiple* compose files be executed serially

    def __post_init__(self):
        self._validate()

    def _validate(self):
        order = self.order
        allowed_orderings = [sorted, sorted_reverse]
        if not order in allowed_orderings:
            raise ValueError(f"Ordering is {order}, has to be in {allowed_orderings}")


COMMANDS = {}


def _register_command(order, name=None, desc=None):
    """Decorator to register a function or method as a command."""

    def decorator(func):
        nonlocal desc, name

        # If the decorated function's actual name and docstring are already proper,
        # we can use them here. Otherwise, they need to be set explicitly.
        if desc is None:
            desc = func.__doc__.splitlines()[0]
        if name is None:
            name = func.__name__

        COMMANDS[name] = CommandMetadata(desc, order)
        LOGGER.debug(f"Registered {name} as a command.")

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._order = order
        return wrapper

    return decorator


_STDERR_CONVERSIONS = {
    compile(
        # Examples for strings that are supposed to match:
        # "error resolving passed in nfs address: lookup nas.lan on 192.168.0.1:53: no such host"
        # "error resolving passed in nfs address: lookup nas.lan on [::1]:53: read udp [::1]:39188->[::1]:53: read: connection refused"
        r"error resolving [\w ]+? address: lookup [\w\.]+? on .+? (read udp|no such host)"
    ): DnsResolutionError,
}


@retry(on_exception=DnsResolutionError)
@log_calls(as_level=logging.DEBUG)
def _run(cmd, subcmd, flags=None, **kwargs) -> CompletedProcess:
    if flags is None:
        flags = []
    else:
        if isinstance(flags, str):
            # Allow flags to be a string, so that we don't have to create a list for a
            # single flag argument (`["--all"]` vs. `"--all"`).
            flags = split(flags)
    try:
        return text_run(cmd + split(subcmd) + flags, **kwargs)
    except CalledTextProcessError as e:
        # Examine the standard error output, trying to find matches. If a match is found,
        # convert raised exception to a more fitting one.
        for regex, exception in _STDERR_CONVERSIONS.items():
            match = regex.search(e.stderr)
            if match:
                LOGGER.warning(
                    f"Process' stderr matched against {regex}, raising {exception}"
                )
                raise exception(**vars(e)) from e

        raise


class CompositionMeta(type):
    def __new__(cls, name, bases, namespace):
        new_cls = super().__new__(cls, name, bases, namespace)

        new_cls._base_cmd = ["docker-compose", "--no-ansi"]

        base_subcommands = {
            name: CommandMetadata(desc, order)
            for name, desc, order in [
                ("build", "Build or rebuild services.", sorted),
                ("config", "Validate and view the Compose file.", sorted),
                ("create", "Create services.", sorted),
                (
                    "down",
                    "Stop and remove containers, networks, images, and volumes.",
                    sorted_reverse,
                ),
                ("events", "Receive real time events from containers.", sorted),
                ("exec", "Execute a command in a running container.", sorted),
                ("help", "Get help on a command.", sorted),
                ("images", "List images.", sorted),
                ("kill", "Kill containers.", sorted),
                ("logs", "View output from containers.", sorted),
                ("pause", "Pause services.", sorted),
                ("port", "Print the public port for a port binding.", sorted),
                ("ps", "List containers.", sorted),
                ("pull", "Pull service images.", sorted),
                ("push", "Push service images.", sorted),
                ("restart", "Restart services.", sorted),
                ("rm", "Remove stopped containers.", sorted),
                ("run", "Run a one-off command.", sorted),
                ("scale", "Set number of containers for a service.", sorted),
                ("start", "Start services.", sorted),
                ("stop", "Stop services.", sorted_reverse),
                ("top", "Display the running processes.", sorted),
                ("unpause", "Unpause services.", sorted),
                ("up", "Create and start containers.", sorted),
                ("version", "Show the Docker-Compose version information.", sorted),
            ]
        }

        # Dynamically provide attributes for each known `docker-compose` command, which
        # runs the corresponding command and passes all flags on. We could also solve
        # this via `__getattr__` in the class definition, but that's ugly and boring,
        # plus we don't get autocompletion on available commands.
        for subcmd, metadata in base_subcommands.items():
            # Keep argument local to lambda using the signature, see also
            # https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result
            def subcmd_factory(subcmd=subcmd):
                """Returns a specialized function with fixed arguments.

                By specifically introducing `command` in the function signature,
                a new scope is created to allow the new returned function to access the
                correct object.
                """

                @_register_command(
                    name=subcmd, desc=metadata.desc, order=metadata.order,
                )
                def subcmd_run(self, flags=None):
                    # For docker-compose, it's important to run in the correct working
                    # directory to resolve all files, e.g. `.env` files.
                    return _run(
                        self._base_cmd, flags=flags, subcmd=subcmd, cwd=self.cwd,
                    )

                return subcmd_run

            name = subcmd.lower()
            LOGGER.debug(f"Providing method '{name}' for {new_cls}.")
            setattr(new_cls, name, subcmd_factory())
        return new_cls


class Composition(metaclass=CompositionMeta):
    def __init__(self, file):
        self.file = Path(file).resolve(strict=True)
        self.cwd = self.file.parent
        self.project = self.cwd.parts[-1]
        with open(self.file) as f:
            self._config = yaml.safe_load(f)

        self._check_validity()

    @property
    def containers(self):
        containers = _DOCKER.containers.list()
        for container in containers:
            labels = container.labels
            try:
                working_dir = Path(labels["com.docker.compose.project.working_dir"])
            except KeyError:  # Not part of any docker-compose service
                continue
            if self.file.parent == working_dir:
                # Part of this docker-compose service
                yield container

    @_register_command(sorted)
    def update(self, remainder):
        """Updates all composition components.

        In docker-compose.yaml, the 'build' and 'image' directives are somewhat mutually
        exclusive. One or the other would be enough: 'build' builds from a provided,
        self-written Dockerfile in some directory (which can contain other files that
        will be copied into the image, just like a normal Dockerfile build process).
        'image' pulls a preexisting image from a registry. Should both be used, an
        image will be built according to 'build' and *named* according to 'image'
        ('name:tag'). Therefore, both *can* occur together, but only one of either is
        strictly required.
        The order of operations here is:
            1. Build all services that rely on "build" (as opposed to "image"), and
                "always attempt to pull a newer version of the image" with the `--pull`
                option.
            2. Pull all latest images for all services that rely on "image" (*without* a
                "build").
            3. Restart after updating.
        """
        parser = argparse.ArgumentParser(
            description=dedent(
                """\
                Updates all server components, rebuilding from any Dockerfiles
                and pulling from image declarations as well as for Dockerfiles.
                Does not take any flags because this prodecure calls multiple
                independent subcommands.
                """
            )
        )
        _ = parser.parse_args(remainder)
        return [self.build("--pull"), self.pull(), self.up("--detach")]

    @_register_command(sorted)
    def lexec(self, remainder):
        """Execute a command on all services with a certain, truthy label.

        There's two types of labels:
            1. Lists simply allow labels to be present, with no value/value of `None`.
            2. Mappings additionally assign values to labels.

        I decided to only allow mappings so that a change in behaviour can be
        triggered in the YAML by flipping the value, not removing the entire label
        (like you would have to do with lists).
        """
        parser = argparse.ArgumentParser(
            description=dedent(
                """\
                Like `exec`, but finds services to operate on automatically, by
                filtering by the passed label.
                The remainder here is forwarded to `exec`, *without* the `SERVICE`
                part (so only the command to execute and flags to that command.).
            """
            )
        )
        parser.add_argument(
            "-e",
            "--exec_options",
            help="Options to be passed to exec itself, not the command to be executed."
            + " WARNING: Must be quoted *in the shell* to avoid wrong processing.",
        )
        parser.add_argument(
            "label", help="Execute on services where this label is truthy."
        )
        parser.add_argument(
            "remainder",
            # For an overview of `nargs`, see also https://stackoverflow.com/a/31243133/11477374
            nargs=argparse.REMAINDER,
            help="Remainder is the command (with flags) to be executed for each"
            + " identified service.",
        )
        args = parser.parse_args(remainder)

        label = args.label
        LOGGER.info(f"Got label '{label}'")

        results = []
        for service_name, service_config in self["services"].items():
            LOGGER.debug(f"Working on service '{service_name}'...")
            try:
                do_exec = bool(service_config["labels"][label])
                LOGGER.debug(f"Found label, evaluated to '{do_exec}'")
            except KeyError:
                LOGGER.debug("No such label, or no labels at all.")
                continue
            except TypeError:
                LOGGER.debug("Labels exist but they are not a mapping.")
                continue
            if do_exec:
                LOGGER.info("Executing on this service.")
                results.append(
                    self.exec(
                        # Examples in comments:
                        split(args.exec_options)  # ['-T']
                        + [service_name]  # ['main']
                        + args.remainder  # ['ls', '-lah']
                    )
                )
        return results

    def __getitem__(self, key):
        return self._config[key]

    def __lt__(self, other):
        """Enable sorting by lexicographical order of their file paths."""
        return self.file < other.file

    def _check_validity(self):
        """Checks if a file is a valid docker-compose file."""
        try:
            self.config("--quiet")  # Don't spam log
        except CalledProcessError as e:
            raise ValueError(
                f"{self.file} is not a valid docker-compose service file"
                f" (stderr='{e.stderr}')."
            ) from e

    def __repr__(self) -> str:
        cls = self.__class__
        return f"{cls.__name__}(file={self.file})"


class Server(Sequence):
    """Holds docker-compose compositions and acts on them according to a command."""

    def __init__(self, root: Path, command: str):
        self.root = Path(root).resolve(strict=True)

        items = root.rglob("docker-compose.y*ml")
        self._compositions = [Composition(item) for item in items]

        self.command = command

    def run(self, remainder: List[str]):
        """Runs the current command on all compositions in their current order."""

        help_only = len(remainder) == 1 and remainder[0] in ["--help", "-h"]
        if not help_only:
            cls = self.__class__.__name__
            LOGGER.info(
                f"Running {cls} command '{self.command}' with remainder '{remainder}'..."
            )

        results = []
        order = getattr(Composition, self.command)._order  # Class lookup
        for composition in order(self):
            action = getattr(composition, self.command)  # Instance lookup

            res = action(remainder)

            if help_only:
                # If only help on a subcommand is requested, print it out *once* and
                # leave.
                LOGGER.debug("Only printing help then exiting.")
                try:
                    print(res.stdout)
                except AttributeError:
                    print("No help available.")
                return
            results.append(res)
        return results

    def __getitem__(self, k):
        return self._compositions[k]

    def __len__(self):
        return len(self._compositions)

    def __repr__(self) -> str:
        cls = self.__class__
        return f"{cls.__name__}(root={self.root}, command={self.command})"
