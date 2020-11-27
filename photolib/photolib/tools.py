"""Couple tools to work on a library of photo files."""

import logging
import mimetypes
from collections import defaultdict, namedtuple
from functools import partial
from pathlib import Path
from typing import Dict, List, Set, Tuple

open = partial(open, encoding="utf8")  # Global default (beware Windows...)


logging.basicConfig(level=logging.DEBUG)


class File(type(Path())):
    """Subtype concrete implementation, see
    https://stackoverflow.com/a/34116756/11477374.
    """

    Mime = namedtuple(
        # Just a more readable representation.
        # Encoding is NOT text encoding, but gzip/compress/...
        "Mime",
        ["type", "encoding"],
    )

    @property
    def mime(self):
        return self.Mime(*mimetypes.guess_type(self))

    def _extract_mimetypes(self):
        try:
            category, subtype = self.mime.type.split("/")
        except AttributeError:  # `None` has no `split`
            return None, None
        else:
            return category, subtype

    @property
    def category(self):
        return self._extract_mimetypes()[0]

    @property
    def subtype(self):
        return self._extract_mimetypes()[1]

    @property
    def full_suffix(self) -> str:
        """Gets all file suffixes instead of just the last one.

        Certain photography programs write metadata sidecare files like `.cr2.xmp`,
        so get *all* suffixes, not just the last one (which is `pathlib.Path.suffix`'s
        default behavior, see https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.suffix.)
        """
        return "".join(self.suffixes)


class Library:
    def __init__(self, root, caching=True):
        self.root = Path(root)
        self.caching = caching

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return f"{cls}('{self.root}')"

    @property
    def caching(self):
        return self._caching

    @caching.setter
    def caching(self, value):
        try:
            caching = self.caching
        except AttributeError:
            # Doesn't exist yet (https://stackoverflow.com/a/41667642/11477374).
            # Ignore and go to finally block.
            pass
        else:
            # Exists, so check its previous value
            switch = caching != value
            if caching and switch:
                # Caching is enabled but switch requested: empty existing cache
                self.clear_cache()
        finally:
            self._caching = value

    def clear_cache(self):
        """Clears existing file cache if it exists."""
        logging.debug("Clearing existing cache...")
        try:
            del self._files
            logging.info("Cleared cache.")
        except AttributeError:
            logging.debug("Nothing to clear.")
            pass

    def _get_files(self, category=None) -> List[File]:
        """Recursively yields all files of a given optional mime category."""
        try:
            all_files = self._files
        except AttributeError:
            # Timsort makes it so that if files already sorted, sorting will be fast.
            all_files = sorted(
                File(item) for item in self.root.rglob("*") if item.is_file()
            )

        if self.caching:
            self._files = all_files

        if category is None:
            files = all_files
        else:
            files = [file for file in all_files if file.category == category]

        return files

    @property
    def files(self):
        return self._get_files(category=None)

    @property
    def image_files(self):
        return self._get_files(category="image")

    @property
    def video_files(self):
        return self._get_files(category="video")

    @property
    def text_files(self):
        return self._get_files(category="text")

    @property
    def media_files(self):
        return sorted(self.image_files + self.video_files)

    @property
    def aux_files(self):
        return sorted(set(self.files) - set(self.media_files))

    @property
    def unique_mimes(self) -> Set[Tuple[str, str]]:
        return {file.mime for file in self}

    def __iter__(self):
        return iter(self.files)

    def __len__(self):
        """The size of a library is the number of its media files."""
        return len(self.media_files)

    def __contains__(self, value):
        return value in self

    def __getitem__(self, key):
        return self.files[key]

    @property
    def mime_files(self) -> Dict[str, List[Path]]:
        """Maps mimetypes (type/encoding tuples) to corresponding files."""
        mime_files = defaultdict(list)
        for file in self:
            mime_files[file.mime].append(file)
        return dict(mime_files)  # Convert back to normal dict for viewing

    @property
    def unique_suffixes(self) -> Set[str]:
        """Gets all occuring unique suffixes."""
        return {file.full_suffix for file in self}

    @property
    def clusters(self):
        """Gets clusters of files with the same stem but different suffixes.

        Many photography programs write metadata sidecar files. This method finds
        all such file groups aka clusters. It also finds all other extensions, e.g.
        JPG. For example, the files:
            - `/home/you/images/hello.raw`,
            - `/home/you/images/hello.xmp`,
            - `/home/you/images/hello.jpg`
        would be found and mapped together here.

        This method only looks for matches of the same name in the *same* directory!

        See also https://photo.stackexchange.com/q/16401.
        """
        clusters = {}
        for file in self:
            stem = file.stem
            stub = str(file.parent) + stem  # Original filepath but without suffix
            if stub in clusters:
                logging.debug(f"Skipping {file}")
                # If a base file has X different extensions, it would be processed X
                # times, but once is enough.
                continue
            # https://stackoverflow.com/a/61296708/11477374
            same_stem_files = [File(f) for f in file.parent.glob("*") if f.stem == stem]
            if len(same_stem_files) > 1:
                suffixes = [f.full_suffix for f in same_stem_files]
                assert len(suffixes) > 1
                clusters[stub] = suffixes
        return clusters

    def dump(self, path=Path("library.txt"), sep="\n"):
        with open(path, "w") as f:
            for file in self:
                f.write(str(file) + sep)
