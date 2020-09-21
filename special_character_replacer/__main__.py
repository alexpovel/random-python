#!/bin/env python3

"""Tool to replace alternative spellings of special characters
(e.g. German umlauts [ä, ö, ü] etc. [ß]) with the proper special characters.
For example, this problem occurs when no proper keyboard layout was available.

This tool is dictionary-based to check if replacements are valid words.
"""

import argparse
import json
import logging
import re
import sys
from functools import partial
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PARSER = argparse.ArgumentParser(description=__doc__)

# Because Windows is being stupid (defaults to cp1252), be explicit about encoding:
open = partial(open, encoding="utf8")

THIS_DIR = Path(__file__).parent

with open(THIS_DIR / Path("language_specials").with_suffix(".json")) as f:
    LANGUAGE_SPECIALS = json.load(f)


PARSER.add_argument(
    "language",
    help="Text language to work with, in ISO 639-1 format.",
    choices=LANGUAGE_SPECIALS,
)

PARSER.add_argument(
    "-c",
    "--clipboard",
    help="Read from and write back to clipboard instead of STDIN/STDOUT.",
    action="store_true",
)

PARSER.add_argument(
    "-f",
    "--force-all",
    help="Force substitutions and return the text version with the maximum number of"
    " substitutions, even if they are illegal words (useful for names).",
    action="store_true",
)

PARSER.add_argument(
    "-d", "--debug", help="Output detailed logging information.", action="store_true",
)

ARGS = PARSER.parse_args()

if USE_CLIPBOARD := ARGS.clipboard:
    # Allows script to be used without installing 3rd party packages if clipboard
    # functionality is not desired.
    import pyperclip

FORCE = ARGS.force_all
LANG = ARGS.language

BASE_DICT_PATH = THIS_DIR / Path("dicts")
BASE_DICT_FILE = Path(LANG).with_suffix(".dic")


if ARGS.debug:
    # Leave at default if no logging/debugging requested.
    logging.basicConfig(level="DEBUG")


def distinct_highest_element(iterable: Iterable, key=None) -> bool:
    """Gets one element if it compares greater than all others according to some key.

    For example, using `key=len`, the list `[(1, 2), (3, 4)]` has two tuples of the
    same length: no value (2 and 2) compares greater than any other. The iterable
    `[(1, 2), (3, 4), (5, 6, 7)]` has an element of length 3, which is greater than
    the second-highest (here: longest, due to the `key`), returning that element.

    If `key` is `None`, the values of elements are compared directly, instead of some
    property (`key`) of those elements. As such, `[1, 1]` fails, but `[1, 1, 2]` etc.
    returns the found element, `2`.

    Args:
        iterable: The iterable to be examined.
        key: The key to compare the iterable elements by. The key must return a sortable
            object (implementing at least `__lt__`). If None, element values are used
            directly.

    Returns:
        The distinctly single-highest element according to the key criterion if it
        exists, else None.
    """
    # If iterable is already sorted, Python's timsort will be very fast and little
    # superfluous work will have to be done.
    iterable = sorted(iterable, key=key)
    highest = iterable[-1]

    try:
        second_highest = iterable[-2]
    except IndexError:
        # Iterable of length one necessarily has one distinct element.
        return highest

    if key is None:
        if highest > second_highest:
            return highest
    if key(second_highest) < key(highest):
        return highest
    # Fell through, implicit `return None`


def read_linedelimited_file(file: Path) -> List[str]:
    with open(file) as f:
        lines = f.read().splitlines()
    logging.debug(f"Fetched {type(lines)} containing {len(lines)} items from {file}")
    return lines


def write_linedelimited_file(file: Path, lines: List[str]):
    with open(file, "w") as f:
        f.write("\n".join(lines))
    logging.debug(f"Wrote file containing {len(lines)} lines to {file}")


def filter_strs_by_letter_occurrence(
    strings: List[str], letter_filters: List[str]
) -> List[str]:
    """Filters a string list by only retaining elements that contain any filter letters.

    Comparison for filtering is caseless.

    Args:
        strings: List to filter.
        letter_filters: List of substrings that elements in the list-to-be-filtered
            must contain to be returned.

    Yields:
        All strings of the original list which contain any string in the filter list.
    """
    for string in strings:
        if any(cf_contains(ltr, string) for ltr in letter_filters):
            logging.debug(f"Yielding '{string}'.")
            yield string


def prepare_processed_dictionary(
    file: Path = BASE_DICT_PATH / Path("containing_specials_only") / BASE_DICT_FILE,
    fallback_file: Path = BASE_DICT_PATH / BASE_DICT_FILE,
    letter_filters: List[str] = None,
) -> List[str]:
    """Provides words from a pre-processed file or additionally creates it if not found.

    Args:
        file: The pre-processed, line-separated file of items.
        fallback_file: File to use and create new file from if main file not found.
        letter_filters: List of substrings items in the fallback file must contain to
            be returned and written to a new, processed file.
    Returns:
        List of words from the read pre-preprocessed file.
    """
    if letter_filters is None:
        letter_filters = []
    try:
        items = read_linedelimited_file(file)
        logging.debug("Found pre-processed list.")
    except FileNotFoundError:
        logging.debug("No pre-processed list found, creating from original.")
        try:
            items = read_linedelimited_file(fallback_file)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Dictionary for '{LANG}' not available.") from e
        logging.debug(f"Fetched unprocessed list.")
        items = list(filter_strs_by_letter_occurrence(items, letter_filters))
        write_linedelimited_file(file, items)
    return items


def cf_contains(element: str, string: str) -> bool:
    """Casefold (aka 'strong `lower()`') check if a substring is in a larger string.

    Args:
        element: The shorter string to bed tested if contained in the larger string.
        string: The larger string.

    Returns:
        Caseless test of whether the larger string contains the shorter string.
    """
    return element.casefold() in string.casefold()


def combinations_any_length(iterable: Iterable[Any]) -> Any:
    """Yields all possible combinations of all possible lengths of an iterable.

    Adapted from https://stackoverflow.com/a/59009314/11477374. For an iterable
    `["A", "B", "C"]`, returns:

    ```
    [
        ['A'],
        ['B'],
        ['C'],
        ['A', 'B'],
        ['A', 'C'],
        ['B', 'C'],
        ['A', 'B', 'C'],
    ]
    ```

    by running `itertools.combinations` with all repeats of essentially
    `range(len(iterable))`.

    Args:
        iterable: The iterable to yield combinations of.

    Yields:
        A viable combination from the iterable.
    """
    for i, _ in enumerate(iterable, start=1):
        subcombinations = combinations(iterable, r=i)
        for item in subcombinations:
            logging.debug(f"Yielding combinatory element {item}.")
            yield item


def substitute_spans(
    string: str,
    spans: List[Tuple[int, int]],
    spans_to_substitutions: Dict[Tuple[int, int], str],
) -> str:
    """Substitutes elements at given positions in a string.

    Works from a list of spans (start, end index pairs) and a mapping of those pairs to
    elements to put in that span instead.

    Args:
        string: The original string to substitute elements in.
        spans: All spans in the string to substitute elements at.
        spans_to_substitutions: A mapping of spans to which element (e.g. a letter) to
            insert at that position, replacing the original.

    Returns:
        The original string with all characters at the given spans replaced according to
        the passed mapping.
    """
    # Reverse to work back-to-front, since during processing, indices
    # change as the string changes length. If starting from the back,
    # this issue is avoided; if starting from the front (non-reverse sorting),
    # later positions would get shifted.
    spans = sorted(spans, reverse=True)

    original_string = string

    for span in spans:
        start, end = span
        substitution = spans_to_substitutions[span]
        # Dynamically modifying strings is bad (inefficient due to immutability), but
        # felt more natural/easier and is unlikely to be an issue.
        string = string[:start] + substitution + string[end:]
    logging.debug(f"Turned '{original_string}' into '{string}'.")
    return string


def represent_strings(
    strings: List[str], separator: str = "|", delimiters: Tuple[str, str] = ("[", "]"),
) -> str:
    """Represents strings as one by joining them, leaving single strings as-is.

    Args:
        strings: The strings to be joined into one unified, larger string.
        separator: The separator to insert between joined substrings.
        delimiters: The two strings to be inserted left and right of the joined string.

    Returns:
        The strings joined into one larger, processed one or the untouched string if
            only one found.
    """
    n_required_delimiters = 2
    n_passed_delimiters = len(delimiters)
    if n_passed_delimiters != n_required_delimiters:
        raise ValueError(
            f"Passed {n_passed_delimiters} delimiters when {n_required_delimiters}"
            " required (left, right)."
        )

    multiple_strings = int(len(strings) > 1)
    delimiters = tuple(delimiter * multiple_strings for delimiter in delimiters)

    if len(strings) == 1:
        # These assertions resulted from what used to be a comment; it is a very wordy
        # and duplicated effort to assert correctness of the above trickery instead of
        # using a more straightforward approach. This is just for fun.
        assert not any(delimiters)
        assert separator.join(strings) == strings[0]

    return delimiters[0] + separator.join(strings) + delimiters[-1]


def main():
    """Perhaps overloaded with logic, but a lot of lines are comments/logging."""
    text = pyperclip.paste() if USE_CLIPBOARD else sys.stdin.read()

    word_regex = re.compile(r"(\w+)")
    assert (
        word_regex.groups == 1
    ), "A (single) capture group is required for re.split to work as intended here."

    # Enforce lowercase so we can rely on it later on. Do not use `casefold` on keys,
    # it lowercases too aggressively. E.g., it will turn 'ß' into 'ss', while keys
    # are supposed to be the special letters themselves.
    specials_to_regex_alts = {
        k.lower(): re.compile(v.casefold(), re.IGNORECASE)
        for k, v in LANGUAGE_SPECIALS[LANG].items()
    }

    known_words = prepare_processed_dictionary(letter_filters=specials_to_regex_alts)

    lines = text.splitlines()
    processed_lines = []
    for line in lines:
        processed_line = []
        items = re.split(word_regex, line)  # Can be words and non-words ("!", "-", ...)
        for item in items:
            # After having split using regex, checking each item *again* here is
            # duplicated effort; however, this is very easy to do. The alternatives are
            # way harder to code, therefore easier to get wrong and harder to maintain.
            is_word = bool(re.match(word_regex, item))
            logging.debug(f"Item '{item}' is a word: {is_word}.")

            # Short-circuits, so saves processing if not a word in the first place
            is_special_word = is_word and any(
                cf_contains(special_alt_letter.pattern, item)
                for special_alt_letter in specials_to_regex_alts.values()
            )
            logging.debug(
                f"Item '{item}' contains potential specials: {is_special_word}."
            )

            if is_special_word:
                # Using spans (start, end pairs) as keys is valid, as they are unique.
                spans_to_substitutions = {}
                for special_letter, regex in specials_to_regex_alts.items():
                    for match in re.finditer(regex, item):
                        logging.debug(f"Found a match ({match}) in item '{item}'.")
                        if any(letter.isupper() for letter in match.group()):
                            # Treat e.g. 'Ae', 'AE', 'aE' as uppercase 'Ä'
                            special_letter = special_letter.upper()
                            logging.debug(f"Treating match as uppercase.")
                        else:
                            # Reset to lowercase, might still be uppercase from last
                            # iteration.
                            special_letter = special_letter.lower()
                            logging.debug(f"Treating match as lowercase.")
                        spans_to_substitutions[match.span()] = special_letter

                # For example, 'Abenteuerbuecher' contains two 'ue' elements, spanning
                # (6, 8) and (10, 12), respectively (as returned by `re.Match.span`).
                # We cannot (easily) determine algorithmically which spans would be the correct
                # ones to substitute at. Therefore, get all possible combinations; in
                # this example: the first, the second, and both (i.e., all combinations
                # of all possible lengths).
                span_combinations = list(
                    combinations_any_length(spans_to_substitutions)
                )
                logging.debug(f"All combinations to be tested are: {span_combinations}")
                logging.debug(
                    f"The underlying mapping for the tests is: {spans_to_substitutions}"
                )

                # Special words can be problematic, e.g. 'Abenteuer'. The algorithm
                # finds 'ue', but the resulting word 'Abenteür' is illegal. Therefore,
                # words with replacements are only *candidates* at first and have
                # to get checked against a dictionary.
                candidates = [
                    substitute_spans(item, spans, spans_to_substitutions)
                    for spans in span_combinations
                ]
                logging.debug(f"Word candidates for replacement are: {candidates}")

                if FORCE:
                    # There exists only one word with "the most substitions"; all others
                    # have fewer. There is no ambiguity as long as the mapping of
                    # alternative spellings to originals is bijective, e.g. 'ue' only
                    # maps to 'ü' and vice versa. This is assumed to always be the case.
                    #
                    # Instead of this convoluted approach, we could also take the
                    # *shortest* candidate, since substitutions generally shorten the
                    # string (e.g. 'ue' -> 'ü'). The shortest string should also have
                    # the most substitutions. However, with Unicode, you never know
                    # how e.g. `len` will evaluate string lengths.
                    # Therefore, get the word that *actually*, provably, has the most
                    # substitutions (highest number of spans).
                    most_spans = distinct_highest_element(span_combinations, key=len)
                    assert most_spans

                    word_with_most_subs = substitute_spans(
                        item, most_spans, spans_to_substitutions
                    )

                    assert word_with_most_subs
                    legal_candidates = [word_with_most_subs]
                    legal_source = "forced"
                else:
                    # Also check lowercase, since words that are usually lowercased
                    # (e.g. 'uebel') in the dictionary might appear capitalized, e.g. at
                    # the start of sentences ('Ueble Nachrede!')
                    legal_candidates = [
                        candidate
                        for candidate in candidates
                        if candidate in known_words or candidate.lower() in known_words
                    ]
                    legal_source = "found in dictionary"
                logging.debug(
                    f"Legal ({legal_source}) word candidates for replacement"
                    f" are: {legal_candidates}"
                )

                if legal_candidates:
                    # ONLY assign to `item` if legal candidates were found at all.
                    # If no legal candidates, all substitutions were wrong: do not
                    # reassign to `item`, so e.g. 'Abenteuer' stays 'Abenteuer'.
                    item = represent_strings(legal_candidates)
            logging.debug(f"Adding item '{item}' to processed line.")
            processed_line.append(item)
        new_line = "".join(processed_line)
        logging.debug(f"Processed line reads: '{new_line}'")
        processed_lines.append(new_line)
    new_text = "\n".join(processed_lines)
    if USE_CLIPBOARD:
        pyperclip.copy(new_text)
    else:
        print(new_text)


if __name__ == "__main__":
    main()
