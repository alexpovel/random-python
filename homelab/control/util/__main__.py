"""Module for miscellaneous operations related to the server."""

import argparse
import io
import json
import tarfile
from functools import partial
from getpass import getpass, getuser
from pathlib import Path
from sys import exit, stderr, stdout

import ipinfo
from control.docker import _DOCKER, docker_logs
from control.util.files import (
    PYTHON_PACKAGE_ROOT,
    PYTHON_PROJECT_ROOT,
    locate_executable,
    strip_last_suffix,
)
from control.util.log import LOGGER
from control.util.misc import pprint
from control.util.time import aware_timestamp, now
from jinja2 import Environment, FileSystemLoader
from jinja2.runtime import StrictUndefined
from pexpect import spawn
from pexpect.exceptions import EOF


class _AutoFill:
    """pexpect calls `flush`/`write` when logging, we intercept and overwrite here.

    Used to replace any written data with a fixed, predetermined string, e.g. to mask
    input passwords while hinting that a prompt has been answered.
    """

    def __init__(self, io, print="<Autofilled>"):
        self._io = io
        self.print = print

    def flush(self):
        self._io.flush()

    def write(self, _):
        return self._io.write(self.print)


def cli_interact(cmd, args, expect, reply, log=stdout):
    with spawn(cmd, args, encoding="utf-8", echo=False) as proc:
        proc.logfile_read = log
        proc.logfile_send = _AutoFill(log)

        while True:
            # Reply to *all* prompts of expected form, e.g, for `systemctl` it prompts
            # for a password twice:
            # 1. `Authentication is required to manage system service or unit files.`
            # 2. `Authentication is required to reload the systemd state.`
            try:
                proc.expect_exact(expect)
                proc.sendline(reply)
            except EOF:
                break
    log.write("\n")
    error_status = proc.exitstatus or proc.signalstatus
    if error_status:
        stderr.write(f"Interaction failed, process returned {error_status}. Exiting.\n")
        stderr.flush()
        exit(error_status)

    return proc


def link(sysctl="systemctl", log=stdout):
    """Renders systemd unit file templates and sets them up (enabling+starting)."""
    template_dir = PYTHON_PACKAGE_ROOT / "util" / "templates"

    env = Environment(
        loader=FileSystemLoader(template_dir),
        undefined=StrictUndefined,  # Don't silently ignore missing inputs
        lstrip_blocks=True,
        trim_blocks=True,
        keep_trailing_newline=True,
    )

    vars = {
        "user": getuser(),
        "workdir": PYTHON_PROJECT_ROOT,
        "poetry": locate_executable("poetry"),
    }

    rendered_dir = template_dir / ".rendered"
    rendered_dir.mkdir(exist_ok=True)

    sysctl_interact = partial(
        cli_interact,
        cmd=sysctl,
        expect="Password:",
        reply=getpass(f"{sysctl} requires your password:"),
        log=log,
    )

    for item in template_dir.iterdir():
        if not item.is_file():
            continue
        name = item.name
        template = env.get_template(name)

        unit_file = strip_last_suffix(rendered_dir / name)
        with open(unit_file, "w") as f:
            f.write(template.render(vars))

        sysctl_interact(args=["link", str(unit_file)])

        unit = unit_file.name
        if unit in ["homelab.service", "homelab_backup.timer"]:
            sysctl_interact(args=["enable", unit])
        if unit.endswith(".timer"):
            sysctl_interact(args=["start", unit])

    print("Linking completed successfully.", file=log)
    print("All units were *enabled*, but only timers were also *started*.", file=log)


def cli_parse(choices) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "action",
        help="Choose from:\n"
        + pprint({cmd: func.__doc__ for cmd, func in choices.items()}),
        choices=choices,
        metavar="action",
    )
    return parser.parse_args()


def get_home_ips():
    """Get all unique IPs from our DynDNS history."""

    container = _DOCKER.containers.get("ddns")
    # No `docker cp` equivalent in the Python API, tar magic is required...
    bytes, _ = container.get_archive("/updater/data/updates.json")
    archive_bytes = b"".join(bytes)
    virtual_file = io.BytesIO(archive_bytes)

    tar = tarfile.open(fileobj=virtual_file)
    member = tar.getmember("updates.json")
    file = tar.extractfile(member)

    contents = file.read().decode("utf8")
    updates = json.loads(contents)

    ips = set()
    for record in updates["records"]:
        for ip_update in record["ips"]:
            ips.add(ip_update["ip"])

    return ips


def ipinfos(ips):
    """Fetches all ipinfo.io details for the passed IPs."""
    dir = Path(__file__).parent
    with open(dir / Path("ipinfo-api-token")) as f:
        access_token = f.read().strip()

    handler = ipinfo.getHandler(access_token)

    return [handler.getDetails(ip).details for ip in ips]


def outsiders(dump=True):
    """Gets all requests originating from outside (not in DynDNS history) IPs."""
    entries = []
    outside_ips = set()
    inside_ips = get_home_ips()

    for n, line in enumerate(docker_logs("proxy")):
        entry = json.loads(line)

        timestamp = aware_timestamp(entry["ts"])
        if n == 0:
            log_start = timestamp.isoformat()
            start_delta = now() - timestamp

        try:
            ip, _ = entry["request"]["remote_addr"].split(":")
        except KeyError:
            # Not a server log line, perhaps a startup log line like
            # '{"level":"warn","ts":1615631067.0608304,"logger":"admin","msg":"admin endpoint disabled"}'
            continue
        if ip in inside_ips:
            continue
        outside_ips.add(ip)
        entries.append(entry)

    ip_infos = ipinfos(outside_ips)

    LOGGER.info(f"Logs start at {log_start}, aka {start_delta} ago.")
    LOGGER.info(f"Found {len(entries)} request(s) from outside IPs.")
    LOGGER.info(f"These came from {len(outside_ips)} unique outside IPs:")
    LOGGER.info(ip_infos)

    if dump:
        dumps = {Path("outside_requests.json"): entries, Path("ipinfos.json"): ip_infos}
        for file, data in dumps.items():
            with open(file, "w") as f:
                LOGGER.info(f"Dumping to {file}.")
                json.dump(data, f, indent=4)

    return entries


def main():
    actions = {"link": link, "outsiders": outsiders}

    args = cli_parse(actions)

    actions[args.action]()


if __name__ == "__main__":
    main()
