"""Interact with the reddit API using `praw`.

For the required login credentials, see https://praw.readthedocs.io/en/latest/getting_started/quick_start.html#authorized-reddit-instances.
"""

import argparse
import getpass
import logging
import time
from itertools import chain
from typing import Literal

import essential_generators
import praw

logging.basicConfig(level=logging.INFO)


def fetch_secret(name: str, args) -> str:
    secret = getattr(args, name)
    if secret is None:
        secret = getpass.getpass(f"Please supply '{name}': ")
    return secret


GEN = essential_generators.DocumentGenerator()


def wipe(
    user,
    timespan: Literal["hour", "day", "week", "month", "year", "all"] = "all",
    limit=None,  # None: fetch as much as possible from reddit API
    **kwargs,  # Container for passed but unused crap
):
    total = 0
    while True:
        # Fetch new batch by API until exhausted; even if `limit=None`, aka fetch as
        # much as possible, API seems to limit to around 100. Therefore, run until done.
        comments = user.comments.top(timespan, limit=limit)
        submissions = user.submissions.top(timespan, limit=limit)
        # Use duck-typing here: `comment` and `submission` objects both have `edit` and
        # `delete` methods, so treat equally here.
        items = chain(comments, submissions)
        n = 0  # Iterator maybe empty, so `enumerate` might never define `n`, so init here
        for n, item in enumerate(items, start=1):
            logging.info(f"Working on {item}...")
            logging.info(f"Permalink is {item.permalink}")
            start = time.time()
            try:
                item.edit(GEN.sentence())
            except praw.exceptions.RedditAPIException as e:
                logging.warning(
                    f"Skipping editing, got: '{e.message}' (not a self-post?)"
                )
            item.delete()
            end = time.time()
            logging.info(f"Edited and deleted {item}, took {end - start:0.2f} seconds.")
        total += n
        if n:
            logging.info(f"Edited and deleted {n} items in this batch.")
        else:
            break
    logging.info(f"Edited and deleted {total} items in total.")
    return total


def subreddits(
    reddit,
    **kwargs,  # Container for passed but unused crap
):
    """Fetches all subreddits the reddit user is subscribed to.

    For some reason, `reddit.user.me().subreddits` doesn't exist, but
    `reddit.user.subreddits` does, so use that.
    """
    subreddits = list(reddit.user.subreddits(limit=None))
    logging.info(
        "User subscribed subreddits are"
        f" {sorted(sub.display_name for sub in subreddits)}"
    )
    return subreddits


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    arg_destinations = {"pw": "password", "secret": "client_secret"}

    parser.add_argument(
        "username",
        help="Regular reddit username",
    )
    parser.add_argument(
        "-p",
        "--password",
        dest=arg_destinations["pw"],
        help="Regular reddit password",
    )
    parser.add_argument(
        "client_id",
        help="Generated reddit 'Script' API client ID, see https://www.reddit.com/prefs/apps/",
    )
    parser.add_argument(
        "-s",
        "--client_secret",
        dest=arg_destinations["secret"],
        help="Generated reddit 'Script' API client secret, see https://www.reddit.com/prefs/apps/",
    )

    cmds = {
        "wipe": wipe,
        "subreddits": subreddits,
    }
    parser.add_argument("command", choices=cmds, help="Command to execute.")

    args = parser.parse_args()

    user = args.username
    id = args.client_id
    # Allow to supply CLI options for scripting and prompting for interactive, secure
    # use (no password in shell history):
    secret = fetch_secret(arg_destinations["secret"], args)
    password = fetch_secret(arg_destinations["pw"], args)

    reddit = praw.Reddit(
        username=user,
        password=password,
        client_id=id,
        client_secret=secret,
        # See https://github.com/reddit-archive/reddit/wiki/API#rules:
        user_agent=f"script:reddit_api:v0.1.0 (/u/{user})",
    )

    user = reddit.user.me()

    command = cmds[args.command]
    # Problem at this point: `command` might take unknown arguments that could not be
    # supplied to `cmds` values, because those arguments where unknown before parsing
    # arguments. There seems no elegant way of solving it, so just feed it all the
    # kwargs it would need.
    # This method will explode in complexity once many functions will all sorts of args
    # are implemented (so, never). It also requires `**kwargs` in all function
    # signatures.
    command(user=user, reddit=reddit)


if __name__ == "__main__":
    main()
