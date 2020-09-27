#!/usr/bin/env python3

"""Converts large, lossless music files to smaller, mobile-friendly versions.

Copies metadata and (cover) images, as well as embedding those images into
the music files' metadata.

Based on `ffmpeg` (called via `subprocess` via `pydub`).
"""

import argparse
import logging
from collections import namedtuple
from pathlib import Path
from shutil import copy2 as copy  # copy2 also copies metadata

import fleep  # get file type from binary header
from mutagen.id3 import APIC, ID3
from pydub import AudioSegment  # just a wrapper for ffmpeg
from pydub.utils import mediainfo  # metadata utility


def read_bytes(file, no_of_bytes=128):
    """
    Open the file in bytes mode, read it, and close the file.
    This is a blatant copy of the existing pathlib Path class method
    of the same name, which doesn't offer an argument for the
    amount of bytes to read.
    According to fleep documentation, first 128 bytes is enough to
    determine the file type from the binary file header.
    """
    with file.open(mode="rb") as f:
        return f.read(no_of_bytes)


def fleepget(source):
    return fleep.get(read_bytes(source))


def copy_if_not_exist(src, dest):
    if not dest.is_file():
        copy(src, dest)  # Copy over as-is
        logging.info(f"Copying succeeded.")
    else:
        logging.info(f"Copying did not succeed: target existed.")


def embed_cover(cover: bytes, file: Path):
    audio = ID3(file)
    audio["APIC"] = APIC(
        encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover,
    )
    audio.save()


parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter, description=__doc__
)

parser.add_argument(
    "source", help="Root of the source music directory.",
)
parser.add_argument(
    "-d",
    "--destination",
    help="Root of the destination music directory.",
    default=Path("out"),
)
parser.add_argument(
    "-e",
    "--extensions",
    help="Extensions of files to convert.",
    default=["flac"],
    nargs="+",
)
parser.add_argument(
    "-t", "--target", help="Target extension to convert to.", default="mp3",
)
parser.add_argument(
    "-b",
    "--bitrate",
    help="Target bitrate in kilobytes.",
    default="128",
    choices=["128", "320"],
)
parser.add_argument(
    "-v",
    "--verbose",
    help="More verbose output (increases with times supplied).",
    action="count",
    default=0,
)

args = parser.parse_args()

verbosity_to_log_levels = {
    0: "WARN",
    1: "INFO",
    2: "DEBUG",
}

logging.basicConfig(level=verbosity_to_log_levels[args.verbose])

source_root = Path(args.source)
destination_root = Path(args.destination)

bitrate = args.bitrate

destination_root.mkdir(exist_ok=True)

extensions = args.extensions
target = args.target
logging.info(f"Extensions to be converted are: {extensions}")
logging.info(f"They are going to be converted to: {target}")

ArtistAlbum = namedtuple("ArtistAlbum", ["artist", "album"])


def main():
    covers = {}  # Map records to covers
    # Visit all subdirectories recursively.
    for source in source_root.rglob("*"):
        # Mirror found directory structure relative to the import root directory
        # over to the export directory, also relative.
        relative = source.relative_to(source_root)

        destination = destination_root.joinpath(relative)

        parts = source.parts
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {destination}")

            record = ArtistAlbum(parts[-2], parts[-1])
            try:
                with open(source / Path("cover.jpg"), "rb") as f:
                    cover = f.read()
                    logging.info(f"Cover image found for {record=}")
            except FileNotFoundError:
                logging.warn(f"No cover image found for {record=}")
                cover = None
            finally:
                # Have to store this for later since search is not depth-first,
                # e.g. when a cover is saved, the next encountered item might be
                # of a different album/artist; embedding the cover into it would
                # be wrong.
                covers[record] = cover

        if not source.is_file():
            continue
        logging.info(f"Found file to be processed: {source}")

        record = ArtistAlbum(parts[-3], parts[-2])  # Last part is music file
        # Load from (hopefully previously) encountered, correct cover image:
        cover = covers.get(record)

        header = fleepget(source)  # Binary file header with file metainfo

        if header.type_matches("audio"):
            logging.info("Detected audio file.")
            # File extension we're dealing with (returned without leading period).
            ext = header.extension[0].lower()

            if ext in extensions:
                logging.info(
                    f"Audio file extension '{ext}' belongs to list of"
                    " conversion candidates, starting conversion."
                )
                # Change extension, else we get e.g. "file.flac" when it's actually an mp3.
                destination = destination.with_suffix("." + target)
                logging.info(f"Target audio file is: {destination}")

                if destination.is_file():
                    logging.info("Conversion did not succeed: target existed.")
                else:
                    AudioSegment.from_file(source).export(
                        destination,
                        format=target,
                        # Copy over metadata.
                        # ffmpeg does this automatically without 'map_metadata' nowadays,
                        # but even with "-map_metadata 0" as the value to the "parameters" key,
                        # this doesn't work for PyDub.
                        # Return empty dict if key not found.
                        tags=mediainfo(source).get("TAG", {}),
                        bitrate=bitrate + "k",  # 320k bitrate mp3 leads to large files
                    )
                    logging.info("Conversion succeeded.")
                    if cover is not None and target.lower() == "mp3":
                        # Only use mp3 to ensure ID3 works.
                        logging.info("Embedding cover image into audio file.")
                        embed_cover(cover, destination)
            else:  # Audio file, but not to be converted.
                logging.info(
                    "Audio file is not a candidate for conversion,"
                    f" starting copy process to: {destination}"
                )
                copy_if_not_exist(source, destination)
        elif header.type_matches("raster-image"):
            # Album covers (jpg, png, ...)
            logging.info(f"File is a raster image (album art): {destination}")
            copy_if_not_exist(source, destination)
        else:
            logging.warning(f"Source item fell through (no criteria met): {source}")


if __name__ == "__main__":
    main()
