#!/usr/bin/env python3

import logging
import sys
from pathlib import Path
from shutil import copy2 as copy  # copy2 also copies metadata

import fleep  # get file type from binary header
from pydub import AudioSegment  # just a wrapper for ffmpeg
from pydub.utils import mediainfo  # metadata utility


logging.basicConfig(
    filename="output.log",
    filemode="w",  # over_w_rite file each time
    level=logging.INFO,  # Only print this level and above
    format="[%(asctime)s] "\
    "%(levelname)s (%(lineno)d): %(message)s"  # Custom formatting
)


def read_bytes(file, no_of_bytes=128):
    """
    Open the file in bytes mode, read it, and close the file.
    This is a blatant copy of the existing pathlib Path class method
    of the same name, which doesn't offer an argument for the
    amount of bytes to read.
    According to fleep documentation, first 128 bytes is enough to
    determine the file type from the binary file header.
    """
    with file.open(mode='rb') as f:
        return f.read(no_of_bytes)


def fleepget(item):
    return fleep.get(read_bytes(item))


def copy_if_not_exist(src, dest):
    if not dest.is_file():
        copy(src, dest)  # Copy over as-is
        logging.info(f"\t\tCopying succeeded.")
    else:
        logging.info(f"\t\tCopying did not succeed: target existed.")


paths = {
    "import": {
        "root": Path.home() / "Music"
    },
    "export": {}
}

# Provide ability to get path from command line argument
try:
    paths["export"]["root"] = Path(sys.argv[1])
except IndexError:
    paths["export"]["root"] = Path.home() / "Music_Export"

paths["export"]["root"].mkdir(exist_ok=True)

extensions = {
    "to_convert": ["flac"],
    # ogg/vorbis would be preferred but mp3 has better (mobile) support
    "target": "mp3"
}
logging.info(f"Extensions to be converted are: {extensions['to_convert']}")
logging.info(f"They are going to be converted to: {extensions['target']}")


# Visit all subdirectories recurvisely.
for item in paths["import"]["root"].rglob("*"):

    # Mirror found directory structure relative to the import root directory
    # over to the export directory, also relative.
    paths["export"]["relative"] = item.relative_to(paths["import"]["root"])

    paths["export"]["full"] = paths["export"]["root"].joinpath(
        paths["export"]["relative"])

    if item.is_dir():
        paths["export"]["full"].mkdir(parents=True, exist_ok=True)
        logging.info(f"Created directory: {paths['export']['full']}")

    if not item.is_file():
        continue
    logging.info(f"Found file to be processed: {item}")

    fileheader = fleepget(item)  # Binary file header with file metainfo

    if fileheader.type_matches("audio"):
        logging.info("\tDetected an audio file.")
        # File extension we're dealing with (returned without leading period).
        ext = fileheader.extension[0].lower()

        if ext in extensions["to_convert"]:
            logging.info(
                f"\tAudio file extension '{ext}' belongs to list of conversion candidates, starting conversion:")
            # The new file, which differs from the 'full' file by its suffix.
            # Change extension, else we get e.g. "file.flac" when it's actually an mp3.
            paths["export"]["new"] = paths["export"]["full"].with_suffix(
                "." + extensions["target"])
            logging.info(f"\t\tTarget audio file is: {paths['export']['new']}")

            if not paths["export"]["new"].is_file():
                AudioSegment.from_file(item).export(
                    paths["export"]["new"],
                    format=extensions["target"],
                    # Copy over metadata.
                    # ffmpeg does this automatically without 'map_metadata' nowadays,
                    # but even with "-map_metadata 0" as the value to the "parameters" key,
                    # this doesn't work for PyDub.
                    # Return empty dict if key not found.
                    tags=mediainfo(item).get("TAG", {}),
                    # bitrate="320k", # 320k bitrate mp3 leads to large files
                    # parameters=["-map_metadata", "0"] # Use "tags" key above
                )
                logging.info("\t\tConversion succeeded.")
            else:
                logging.info("\t\tConversion did not succeed: target existed.")
        else:  # Audio file, but not to be converted.
            logging.info(
                f"\tAudio file is not a candidate for conversion, starting copy process to: {paths['export']['full']}")
            copy_if_not_exist(item, paths["export"]["full"])
    elif fileheader.type_matches("raster-image"):
        # Album covers (jpg, png, ...)
        logging.info(
            f"\tFile is a raster image (album art): {paths['export']['full']}")
        copy_if_not_exist(item, paths["export"]["full"])
    else:
        logging.warning(f"Item fell through (no criteria met): {item}")
