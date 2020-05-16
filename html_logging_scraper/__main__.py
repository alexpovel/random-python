#! /bin/env python3

import json
import random
from functools import partial
from importlib.resources import open_text
from smtplib import SMTP_SSL

import requests


def strings_similarity(*strings) -> float:
    """Returns percentage of shared characters among all strings, based on position.

    Iterates over all given strings character-by-character. If all characters
    in a position are equal, gain one point. Iteration stops with the shortest
    string.
    This really only works for long strings that differ in some characters, but
    continue equally afterwards, like:
        abcdefgh_1_jklmnop
        abcdefgh_2_jklmnop
    For more advanced comparisons, use Levenshtein distance.

    Returns:
        Number of points divided by the shortest string's length.
    """
    equal_characters = 0
    for i, characters in enumerate(zip(*strings), start=1):
        if len(set(characters)) == 1:  # all elements equal
            equal_characters += 1
    shortest_length = i
    return equal_characters / shortest_length


def strings_fuzzy_equality(*strings, threshold=0.98) -> bool:
    """Returns whether string similarity is above threshold."""
    return strings_similarity(*strings) >= threshold


def send_mail(
    smtp_server, smtp_username, smtp_password, from_address, to_address, subject, body
):
    with SMTP_SSL(smtp_server) as smtp_connection:
        smtp_connection.login(smtp_username, smtp_password)
        smtp_connection.sendmail(
            from_address,
            to_address,
            (f"Subject: {subject}\n\n{body}"),
        )


def main():
    # 403 Forbidden if no User-Agent set,
    # copied from visiting the site on Windows/Firefox
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) "
            "Gecko/20100101 Firefox/76.0"
        )
    }

    with open_text("html_logging_scraper", "user_config.json") as user_file:
        config = json.load(user_file)

    email_config = config["email"]
    url = config["website"]["url"]

    mail = partial(
        send_mail,
        email_config["smtp_server"],
        email_config["username"],
        email_config["password"],
        email_config["from_address"],
        email_config["to_address"],
    )

    try:
        current_page = requests.get("http://oijfrjoiroijr.com", headers=headers).text
    except requests.ConnectionError as e:
        mail(f"{url} is unreachable!", f"Got:\n\t{e}")
        raise  # let it fail normally

    logfile = "website.html"

    try:
        with open(logfile) as file:
            previous_page = file.read()
    except FileNotFoundError:  # log file does not exist yet
        pass  # to 'finally'
    else:  # no exception: file exists
        if not strings_fuzzy_equality(current_page, previous_page):
            pass  # TODO: only email in this block; for debugging, always email
        mail("Watched website changed significantly!", f"Check it out: {url}")
    finally:
        # Log current page and be done
        with open(logfile, "w") as file:
            file.write(current_page)


if __name__ == "__main__":
    fire_once_in = 10  # by chance, only fire every <int> calls
    if not random.randrange(0, fire_once_in):  # fire on 0
        main()
