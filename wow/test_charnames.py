#!/bin/env python3

"""WIP script to automate typing character names and testing for their availability
in World of Warcraft.

Currently tests all two-character names, the minimum length.
Never used this, didn't fancy risking a ban.
Definitely never use this script either. You'd be a nasty, nasty boy.
"""

import logging
import random
import string
import time
from dataclasses import dataclass
from itertools import product

import keyboard
from rich.progress import track

logging.basicConfig(level=logging.DEBUG, filename="wow_names.log")


def random_wait(circa_seconds, std_dev_factor=None):
    logging.debug(f"Requested {circa_seconds=}")
    if not circa_seconds:
        # noop, e.g. when requesting to wait 0 seconds
        return

    if std_dev_factor is not None:
        std_deviation = circa_seconds * std_dev_factor
    else:
        std_deviation = circa_seconds * 0.1
    logging.debug(f"{std_deviation=}")

    seconds = random.gauss(circa_seconds, std_deviation)
    seconds = abs(seconds)  # If normal distribution runs into negatives

    logging.debug(f"Sleeping for {seconds=}...")
    time.sleep(seconds)


@dataclass
class TypingSpeed:
    letters: float = 0.20  # Tested by typing a text for a minute then counting
    specials: float = letters * 1.5  # Just estimation


def type_key(key, *wait_args):
    logging.debug(f"Pressing '{key=}'...")
    keyboard.press_and_release(key)

    random_wait(*wait_args)


def main():
    two_letter_words = [
        "".join(letters) for letters in product(string.ascii_lowercase, repeat=2)
    ]

    server_answer_seconds = 3

    for word in track(two_letter_words):
        assert word.islower()
        logging.debug(f"{word=}")

        for i, letter in enumerate(word):
            if i:
                keycmd = letter
                wait_time = TypingSpeed.letters
            else:  # Start of iterable
                # Capitalize, like a human (cannot type capital letters directly)
                keycmd = "SHIFT + " + letter
                wait_time = TypingSpeed.specials  # Takes longer to press

            type_key(keycmd, wait_time)

        # Submit and wait for server response:
        type_key("ENTER", server_answer_seconds)

        # Dismiss "Name Taken" dialog:
        type_key("ENTER", TypingSpeed.specials)

        # Delete entered text:
        for _ in range(len(word)):
            # Pressing same key multiple times, which is faster
            type_key("BACKSPACE", TypingSpeed.specials * 0.5)

        random_wait(0.2)  # Extra wait before next one


keyboard.add_hotkey("CTRL + SHIFT + ALT + Q", main, trigger_on_release=True)

keyboard.wait("ESC")
