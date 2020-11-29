"""Couple tools to work on a library of photo files."""

from __future__ import annotations  # https://stackoverflow.com/q/33533148/11477374

import logging
import mimetypes
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from functools import cached_property, partial
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

logging.basicConfig(level=logging.DEBUG)


class DictIndex(IntEnum):
    """For indexing into (key, value) tuples of dictionaries."""

    KEYS = 0
    VALUES = 1


def filter_dict(dct: dict, predicate: Callable, filter_on: DictIndex) -> dict:
    """Filters a dictionary on either values or keys using a predicate.

    Args:
        dct: The dictionary to filter.
        predicate: A callable to apply to each element. If it evaluates True-ish, this
            `dct` entry will be included in the result.
        filter_on: Whether to filter (i.e., apply the predicate) on keys (index 0) or
            values (index 1).

    Returns:
        The passed dictionary with only those entries where either the key or value
        (as specified by the caller) evaluated True-ish according to the predicate.
    """
    # Build a literal tuple and index into it directly.
    return {k: v for k, v in dct.items() if predicate((k, v)[filter_on])}


@dataclass(frozen=True)  # Frozen -> immutable -> __hash__ is provided for us
class Mime:
    """https://en.wikipedia.org/wiki/Media_type#Common_examples"""

    type: Optional[str]  # text, image, video, ...
    subtype: Optional[str]  # jpg, gif, csv, mp4, ...
    # Associated extensions:
    extensions: Optional[Iterable[str]] = field(default=None, repr=False)
    # NOT text encoding, but gzip/compress/...:
    encoding: Optional[str] = field(default=None, repr=False)

    _sep = "/"  # e.g. 'text/csv'

    @classmethod
    def from_path(cls, path: Path) -> Mime:
        mimetype, encoding = mimetypes.guess_type(path)
        return cls.from_string(mimetype=mimetype, encoding=encoding)

    @classmethod
    def from_string(cls, mimetype: Optional[str], **kwargs) -> Mime:
        if mimetype is None:
            type = subtype = mimetype
        else:
            type, subtype = mimetype.split(cls._sep)
        return cls(type, subtype, **kwargs)

    # staticmethod properties aren't a thing, but classmethod properties are possible
    # since Python 3.9: https://docs.python.org/3/howto/descriptor.html#class-methods
    @classmethod
    @property
    def types_map(cls) -> dict[str, Mime]:
        return {
            # Use same mapping as mimetypes module but parse into proper objects:
            extension: cls.from_string(mimetype)
            for extension, mimetype in mimetypes.types_map.items()
        }

    @classmethod
    @property
    def known_mimetypes(cls) -> list[Mime]:
        return sorted(set(cls.types_map.values()))

    @classmethod
    @property
    def known_types(cls) -> list[str]:
        return sorted({mimetype.type for mimetype in cls.known_mimetypes})

    @classmethod
    @property
    def known_subtypes(cls) -> list[str]:
        return sorted({mimetype.subtype for mimetype in cls.known_mimetypes})

    @classmethod
    @property
    def known_extensions(cls) -> list[str]:
        return sorted(cls.types_map)

    def __str__(self) -> str:
        # The following also works if type and/or subtype is None, for which
        # `_sep.join` doesn't work anymore.
        return f"{self.type}{self._sep}{self.subtype}"

    def __lt__(self, other) -> bool:
        """Required for sorting instances of this class (uses `<`).

        https://docs.python.org/3/library/stdtypes.html#list.sort
        """
        return str(self) < str(other)


def register_custom_mimetypes():
    mimetypes.init()

    # Just inited, but maybe something went wrong, so warn about that.
    if not mimetypes.inited:
        raise ValueError("Mimetypes init overwrites custom changes, so init first.")

    custom_mimes = [
        # https://en.wikipedia.org/wiki/Extensible_Metadata_Platform:
        Mime("text", "metadata", extensions=[".xmp"]),
        # https://en.wikipedia.org/wiki/Raw_image_format:
        Mime(
            "image",
            "raw",
            extensions=[
                ".3fr",
                ".ari",
                ".arw",
                ".bay",
                ".braw",
                ".cap",
                ".cr2",
                ".cr3",
                ".crw",
                ".data",
                ".dcr",
                ".dcs",
                ".dng",
                ".drf",
                ".eip",
                ".erf",
                ".fff",
                ".gpr",
                ".iiq",
                ".k25",
                ".kdc",
                ".mdc",
                ".mef",
                ".mos",
                ".mrw",
                ".nef",
                ".nrw",
                ".obm",
                ".orf",
                ".pef",
                ".ptx",
                ".pxn",
                ".r3d",
                ".raf",
                ".raw",
                ".rw2",
                ".rwl",
                ".rwz",
                ".sr2",
                ".srf",
                ".srw",
                ".tif",
                ".x3f",
            ],
        ),
    ]

    for mime in custom_mimes:
        logging.debug(f"Adding '{mime}' to known mimetypes.")
        for extension in mime.extensions:
            mimetypes.add_type(str(mime), extension)
            logging.debug(f"Added extension {extension} to '{mime}'.")


register_custom_mimetypes()


class File(type(Path())):
    """Subtype concrete implementation, see
    https://stackoverflow.com/a/34116756/11477374.
    """

    @cached_property
    def mime(self):
        return Mime.from_path(self)

    @property
    def type(self):
        return self.mime.type

    @property
    def subtype(self):
        return self.mime.subtype

    @property
    def encoding(self):
        return self.mime.encoding

    @property
    def full_suffix(self) -> str:
        """Gets all file suffixes instead of just the last one.

        Certain photography programs write metadata sidecare files like `.cr2.xmp`,
        so get *all* suffixes, not just the last one (which is `pathlib.Path.suffix`'s
        default behavior, see https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.suffix.)
        """
        return "".join(self.suffixes)

    @property
    def stub(self):
        """Returns the file path with all suffixes removed.

        https://stackoverflow.com/a/56807917/11477374"""
        cls = self.__class__
        return cls(str(self).removesuffix(self.full_suffix))


def cluster(files: Iterable[File]) -> dict[File, list[str]]:
    """Maps files with same stems to their multiple suffixes, if present.

    Many photography programs write metadata sidecar files. This method finds
    all such file groups aka clusters. It also finds all other extensions, e.g.
    JPG. For example, the files:
        - `/home/you/images/hello.raw`,
        - `/home/you/images/hello.xmp`,
        - `/home/you/images/hello.raw.xmp`,
        - `/home/you/images/hello.jpg`
    would be found and mapped together here, with the key being the stub (all path
    parts except for the full suffix), the value being a list of *all* found
    suffixes.

    See also https://photo.stackexchange.com/q/16401.

    Args:
        files: List of files to cluster.

    Returns:
        Mapping of all path stubs (full path without (full) suffix) to the founds
        extensions.
        If a filepath has a unique stem, aka only one extension occurs, it is not
        included.
    """
    clusters = defaultdict(list)
    for file in files:
        clusters[file.stub].append(file.full_suffix)
    # Assemble first, filter afterwards, doesn't work otherwise.
    return filter_dict(clusters, lambda x: len(x) > 1, DictIndex.VALUES)


class Library:
    def __new__(cls, *args, **kwargs) -> Library:
        # Provide automatic methods derived from files and known MIME types, e.g. an
        # `image_files` method. This saves us from having to manually add properties for
        # each MIME type with lots of repetition.

        types = Mime.known_types  # 'image', 'video', ...
        # Do not generate for all known subtypes automatically, way too many. Pick a
        # few that make sense:
        subtypes = ["raw", "metadata"]

        for type_ in types + subtypes:
            subtype = type_ in Mime.known_subtypes  # False implies normal 'type'
            sub = "sub" if subtype else ""
            logging.debug(f"Identified {type_} as a {sub}type.")

            # Methods like `image_files`, `video_files`, `raw_files`, to access all
            # files of that type quickly and help with discovery.
            filter_getter = partial(cls.filter, types=[type_], subtype=subtype)
            files_attr = type_ + "_files"
            setattr(cls, files_attr, property(filter_getter))

            # Methods like `image_clusters`, `video_clusters`, `raw_clusters`, again
            # for quick access and discovery.
            def cluster_getter(self, name=files_attr):
                """Delegate from instance variables (self) to outside function.

                Warning: *all* variables used in this function body need to be function
                arguments. Otherwise, closures happen and those closed-over variables
                won't assume their proper values.
                """
                return cluster(files=getattr(self, name))

            setattr(cls, type_ + "_clusters", property(cluster_getter))
        return super().__new__(cls)

    def __init__(self, root) -> None:
        self.root = Path(root)

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return f"{cls}('{self.root}')"

    def filter(self, types: Iterable[str], subtype: bool = False) -> list[File]:
        """Filters all files according to MIME (sub)types.

        Args:
            types: Names of MIME types to filter by (normal types like `image`, `video`,
                ...) or subtypes like `pdf`, `csv`, or custom subtypes.
            subtype: Whether the passed type names are matched against normal or
                subtypes.

        Returns:
            Sorted list of all file paths found matching the request MIME types.
        """
        type_ = "subtype" if subtype else "type"
        logging.debug(f"Fetching files by matching against these {type_}s: {types}.")
        files = []
        for type in types:
            add_files = [file for file in self if getattr(file, type_) == type]
            if not add_files:
                logging.warning(f"'{type}' files requested but none found.")
            files.extend(add_files)
        if not files:
            logging.warning(f"No files found.")
        return sorted(files)

    def clear_cache(self) -> None:
        """Clears any existing caches."""
        logging.debug("Clearing any caches...")
        cls = self.__class__
        for attr, value in vars(cls).items():
            if isinstance(value, cached_property):
                try:
                    del vars(self)[attr]  # Delete from INSTANCE `__dict__`, not class
                except KeyError:
                    pass  # Doesn't exist yet
                else:
                    logging.debug(f"Cleared {attr} cache.")

    @cached_property
    def files(self) -> list[File]:
        logging.info("Fetching current files...")
        return sorted(File(item) for item in self.root.rglob("*") if item.is_file())

    @cached_property
    def clusters(self) -> dict[File, list[str]]:
        logging.info("Clustering all files...")
        return cluster(self)

    @property
    def camera_files(self) -> list[File]:
        return sorted(self.filter(["image", "video"]))

    @property
    def media_files(self) -> list[File]:
        return sorted(self.camera_files + self.filter(["audio"]))

    @property
    def non_media_files(self) -> list[File]:
        return sorted(set(self) - set(self.media_files))

    @property
    def bitmap_files(self) -> list[File]:
        return sorted(
            set(self.filter(["image"])) - set(self.filter(["raw"], subtype=True))
        )

    @property
    def bitmap_clusters(self) -> dict[File, list[str]]:
        return cluster(self.bitmap_files)

    @property
    def non_metadata_files(self) -> list[File]:
        return sorted(set(self) - set(self.filter(["metadata"])))

    @property
    def unique_mimes(self) -> list[Mime]:
        """Gets all occurring unique MIME types."""
        return sorted({file.mime for file in self})

    @property
    def unique_suffixes(self) -> list[str]:
        """Gets all occurring unique full suffixes."""
        return sorted({file.full_suffix for file in self})

    @property
    def mime_files_map(self) -> dict[Mime, list[File]]:
        """Maps mimetypes (type/encoding tuples) to corresponding files."""
        mime_files = defaultdict(list)
        for file in self:
            mime_files[file.mime].append(file)
        return dict(mime_files)  # Convert back to normal dict for viewing

    def __iter__(self) -> Iterator[File]:
        return iter(self.files)

    def __len__(self):
        return len(self)

    def __contains__(self, value):
        return value in self

    def __getitem__(self, key):
        return self.files[key]

    def __call__(self):
        """Allows to work cache-free, aka fetch live files every time, by calling the
        instance:
            `library.image_files` -> uses cache
            `library().image_files` -> clears cache, then resumes as normal
        """
        self.clear_cache()
        return self

    def write(self, filename="library.txt", sep="\n"):
        with open(Path(filename), "w", encoding="utf8") as f:
            for file in self:
                f.write(str(file) + sep)
