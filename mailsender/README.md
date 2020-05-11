# Send a simple email via SMTP

This can for example be run in a cron job:

```text
0 13 * * 1-5  cd /home/pi/dev/random_python && $(which python3) -m mailsender
```

which [says](https://crontab.guru/#0_13_*_*_1-5): *At 1pm on every day of the week, from Monday through Friday*.

Note how the `mailsender` directory is executed as a *package*.
It is a package because it contains `__init__.py`.
Running a package directly causes its `__main__.py` file to be executed.
Running directly fails if that file is not present.
Using a Python package is convenient for many reasons, for example for using `importlib.resources`.

---

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
