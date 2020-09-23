from contextlib import nullcontext

import pytest

from special_character_replacer import distinct_highest_element

VOID = None  # Placeholder for parameters that do not matter in that instance


class TestFunctions:
    @pytest.mark.parametrize(
        ["iterable", "key", "element", "expectation"],
        [
            # Empty iterables
            ([], None, VOID, pytest.raises(IndexError)),
            ((), None, VOID, pytest.raises(IndexError)),
            ("", None, VOID, pytest.raises(IndexError)),
            ({}, None, VOID, pytest.raises(IndexError)),
            #
            # Single-element iterables
            ([1], None, 1, nullcontext()),
            ((1, ), None, 1, nullcontext()),
            ("1", None, "1", nullcontext()),
            ({"1": None}, None, "1", nullcontext()),
            #
            # Non-iterables
            ((1), None, VOID, pytest.raises(TypeError)),  # Not actually a tuple
            (None, None, VOID, pytest.raises(TypeError)),
            (1, None, VOID, pytest.raises(TypeError)),
            #
            # Multi-element iterables w/ single distinct highest element
            ([1, 2, 3], None, 3, nullcontext()),
            ((1.0, 2.0, 3.0), None, 3, nullcontext()),
            ("abc", None, "c", nullcontext()),
            ([(1, 2), (1, 3)], None, (1, 3), nullcontext()),
            #
            # Multi-element iterables w/o single distinct highest element
            ([1, 2, 3, 3], None, None, nullcontext()),
            ((1.0, 2.0, 3.0, 3.0), None, None, nullcontext()),
            ("abcc", None, None, nullcontext()),
            ([(1, 2), (1, 3), (1, 3)], None, None, nullcontext()),
            #
            # Multi-element iterables w/ key and w/o single distinct highest element
            ([[], []], len, None, nullcontext()),
            ([1, 2, 3], len, VOID, pytest.raises(TypeError)),  # int has no len
            ((1.0, 2.0, 3.0), len, VOID, pytest.raises(TypeError)),
            ("abc", len, None, nullcontext()),  # all chars in str same length
            ([(1, 2), (1, 3)], len, None, nullcontext()),  # all tuples same length
            #
            # Multi-element iterables w/ key and w/o single distinct highest element
            ([1, 2, 3, 3], len, VOID, pytest.raises(TypeError)),
            ((1.0, 2.0, 3.0, 3.0), len, VOID, pytest.raises(TypeError)),
            ("abcc", len, None, nullcontext()),  # all chars in str same length
            ([(1, 2), (1, 3), (1, 3)], len, None, nullcontext()),
            #
            # Multi-element iterables w/ key and w/ single distinct highest element
            ("a", len, "a", nullcontext()),
            (["b", "b", "bb"], len, "bb", nullcontext()),
            (["a", "b", "cc"], len, "cc", nullcontext()),
            ([(), (1, )], len, (1, ), nullcontext()),
            ([(1, )], len, (1, ), nullcontext()),
            ([(1, 2), (1, 3), (1, 2, 3)], len, (1, 2, 3), nullcontext()),
            #
            ([1, 2, 3], "Not a callable", VOID, pytest.raises(TypeError))
        ],
    )
    def test_distinct_highest_element(self, iterable, key, element, expectation):
        with expectation:
            assert distinct_highest_element(iterable, key) == element


# def test_version():
#     assert __name__ == "0.1.0"
