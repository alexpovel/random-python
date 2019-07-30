#! /usr/bin/python3
# Script to delete auxiliary files whose parents aren't present anymore
import logging
import os
import sys
from pathlib import Path


logging.basicConfig(
    # filename=os.path.join(root_dir, os.path.basename(__file__).split(".")[0] + ".log"),
    filename=Path(__file__).stem + ".log",
    filemode="w",  # over_w_rite file each time
    level=logging.DEBUG,  # Only print this level and above
    format=#"[%(asctime)s] %(levelname)s (%(lineno)d): "\
        "%(message)s"  # Custom formatting
)

suffixes = {
    "aux": ["xmp"],
    "parent": ["ARW", "CR2"]
}


try:
    root_dir = sys.argv[1]
    logging.info("Setting root directory: " + root_dir)
    debugging = False
except IndexError:
    root_dir = "./testdata_1/2019/2"
    logging.info("No root directory given, working on default: " + root_dir)
    debugging = True
    logging.info("For safety, setting debugging to: " + str(debugging))

if not os.path.isdir(root_dir):
    raise NotADirectoryError("Supplied root directory " + str(root_dir) + " does not exist.")



for directory, subdirs, files in os.walk(root_dir):
    logging.info("\t" + directory)
    if subdirs:
        for subdirname in subdirs:
            logging.info("\t"*2 + subdirname)
    if files:
        base_files = {x.split(".")[0] for x in files}
        logging.debug(base_files)
        for base_file in base_files:
            for parent_suffix in suffixes["parent"]:
                parent_file = ".".join([base_file, parent_suffix])
                if os.path.isfile(os.path.join(directory, parent_file)):
                    logging.info("\t"*3 + "Parent file found: " + parent_file)
                    break
            else:
                logging.info("\t"*3 + "No parent file found: " + base_file)
                for file in files:
                    for suffix in suffixes["aux"]:
                        if file.startswith(base_file) and file.endswith(suffix):
                            if debugging:
                                logging.warning("\t"*4 + "Deleting: " + file)
                            else:
                                logging.warning("\t"*4 + "Actually deleting: " + file)

