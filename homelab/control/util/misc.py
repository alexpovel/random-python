from functools import partial
from math import ceil


def pprint(d: dict, indent=1 * "\t"):
    """Pretty-formats a mapping into a two-column, line-separated string."""

    # Make first column wide enough to accomodate for entries:
    tab_width = 8
    max_item_length = max(len(item) for item in d)
    # The longest entry gets exactly one tab to fill the column gap, the shortest gets
    # the maximum number:
    n_tabs = lambda item: ceil(max_item_length / tab_width) - len(item) // tab_width

    # For pretty, predictable output, sort alphabetically:
    keys = sorted(d.keys())
    lines = [indent + k + n_tabs(k) * "\t" + (d[k] or "") for k in keys]
    return "\n".join(lines)


sorted_reverse = partial(sorted, reverse=True)
