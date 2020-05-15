#! /bin/env python3

import json
import random
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

    current_page = requests.get(url, headers=headers).text

    logfile = "website.html"

    try:
        with open(logfile) as file:
            previous_page = file.read()
    except FileNotFoundError:  # log file does not exist yet
        pass  # to 'finally'
    else:  # no exception: file exists
        if not strings_fuzzy_equality(current_page, previous_page):
            pass  # TODO: only email in this block; for debugging, always email
        with SMTP_SSL(email_config["smtp_server"]) as smtp_connection:
            smtp_connection.login(email_config["username"], email_config["password"])
            smtp_connection.sendmail(
                email_config["from_address"],
                email_config["to_address"],
                (
                    "Subject: Watched website changed significantly!\n\n"
                    f"Check it out: {url}."
                ),
            )
    finally:
        # Log current page and be done
        with open(logfile, "w") as file:
            file.write(current_page)


if __name__ == "__main__":
    fire_once_in = 10  # by chance, only fire every <int> calls
    if not random.randrange(0, fire_once_in):  # fire on 0
        main()
