# Send a simple email via SMTP

## Automate

To automate the sending, consider two options.

### cron job

For example:

```text
0 13 * * 1-5  cd /home/<user>/path/to/repo && $(which python3) -m mailsender
```

which [says](https://crontab.guru/#0_13_*_*_1-5): *At 1pm on every day of the week, from Monday through Friday*.

A much better alternative to `cron` jobs is using `systemd`.

### systemd

Using `systemd` *services* with *timers* can [replace `cron` jobs](https://wiki.archlinux.org/index.php/Systemd/Timers).
For more info next to the this, see [here][DigitalOcean].

A service file could be:

```text
[Unit]
Description=Send a mail via Python

[Service]
# Type=oneshot is default
Type=oneshot

# User= is required to find ~/.ssh for GitHub.
# Otherwise, User=root is default, which will fail to find keys
User=<user>

WorkingDirectory=/home/<user>/path/to/repo

# Pull in latest remote changes, e.g. changed email body
ExecStartPre=/usr/bin/git pull
ExecStart=/usr/bin/python3 -m mailsender
```

at `/etc/systemd/system/servicename.service`.
For info on the syntax, see [here](https://www.freedesktop.org/software/systemd/man/systemd.service.html).
The service, to run scheduled, requires a `.timer` unit:

```text
[Unit]
Description=Run mail sending regularly

[Timer]
OnCalendar=Mon..Fri *-*-* 13:00:00

[Install]
# In order to 'enable', aka run after boot, units require
# a target to be wanted by. multi-user.target loads last,
# so latch onto that.
WantedBy=multi-user.target
```

For more info on `WantedBy`, see [DigitalOcean] again or [here](https://unix.stackexchange.com/a/339537/374985).
The `OnCalendar` key controls the timing.
For its syntax, see [here](https://www.freedesktop.org/software/systemd/man/systemd.time.html#).

---

Running

```bash
systemctl enable --now servicename.timer
```

will *enable* the timer unit, aka allow it to start at boot-up.
The `--now` option will also allow it to *start* *now*, see [here](https://superuser.com/a/1512436/1144470).

The timer now runs and calls its `.service` of the same name automatically.
Therefore, there is no need to start the `.service` or equip it with an `[Install]` section.

## Python Package

Note how, in any case, the `mailsender` directory is executed as a *package*.
It is a package because it contains `__init__.py`.
Running a package directly causes its `__main__.py` file to be executed.
Running directly fails if that file is not present.
Using a Python package is convenient for many reasons, for example for using `importlib.resources`.

## Sieve Filtering

A useful feature for the recipient might be to forward the received email based
on some conditions.
This can be achieved using [Sieve filtering](http://sieve.info/).

```sieve
require ["fileinto"];

if allof (address :is "from" "from@this.address.com") {
    fileinto "INBOX";
    redirect "forward@to.this.address.com";
}
```

This stores a copy of the message in your own inbox and forwards the message.
You can also move to `"TRASH"`, for example, or discard it altogether.

[DigitalOcean]: https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files
