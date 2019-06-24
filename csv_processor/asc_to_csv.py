import json  # JavaScript Object Notation for metadata file
import logging  # log events (more functionality than print())
import math  # pi etc.
import re  # regular expressions
# from collections import defaultdict
from datetime import datetime
from pathlib import Path

import dateutil  # date parsing
import matplotlib.pyplot as plt  # plotting
import pandas  # Data processing
import pytz  # timezone
from matplotlib.backends.backend_pdf import PdfPages


logging.basicConfig(
    filename="out.log",
    filemode="w",  # over_w_rite file each time
    level=logging.INFO,  # Only print this level and above
    format="[%(asctime)s] "\
    "%(levelname)s (%(lineno)d): %(message)s"  # Custom formatting
)


def value_cleanup(raw_in) -> float:
    """
    Turn dirtied string(s) (e.g. ",233 kg") to float(s).
    Apply int(value_cleanup()) if you want to turn this function's output
    into an integer again, in case it came out as float.
    """
    # If input is already 'clean', i.e. an integer, float or datetime object,
    # don't manipulate it:
    if isinstance(raw_in, (int, float, datetime)) or raw_in is None:
        return raw_in
    # If input is a list of dirtied strings, we return a list of cleaned output.
    # This also works on arbitrarily nested lists (recursion):
    elif isinstance(raw_in, list):
        return [value_cleanup(dirtied_string) for dirtied_string in raw_in]
    # If input is a dictionary, clean up the values and leave the keys:
    elif isinstance(raw_in, dict):
        return {k: value_cleanup(v) for k, v in raw_in.items()}
    # Before finally working on the string, filter out anything that hasn't been
    # filtered yet.
    elif not isinstance(raw_in, str):
        raise TypeError(f"Expected string, got '{type(raw_in).__name__}'.")
    else:
        decimal_sep = "."  # Proper decimal separator for Python
        # Fix decimal representation for European data:
        dotted = raw_in.replace(",", decimal_sep)

        stripped = dotted.strip()  # Remove surrounding whitespace
        numeric = "-0123456789" + decimal_sep  # Include negatives/decimal sep.
        position = None  # Initialize to throw error just in case
        # Append space for search to work
        for position, char in enumerate(stripped + " "):
            if char not in numeric:
                if position == 0:  # Didn't even start with numerical char
                    return None
                break
        # When no decimal separator is found in the original (either "," or ".")
        # it should be handled as an integer.
        # Get cleaned-up string up until the position found for the first
        # non-numeric character:
        cleaned = stripped[:position]
        if not decimal_sep in cleaned:
            final_value = int(cleaned)
        else:
            final_value = float(cleaned)

        logging.info(f"Turned {type(raw_in).__name__} '{raw_in}' into "
                     f"{type(final_value).__name__} '{final_value}'.")
        return final_value


def get_metadata(table, data_start: int) -> dict:
    """
    Take in a table file handle and extract the meta-info found in the file
    header, put into dictionary. After the header, the column names, i.e.
    row of column header names follows; return its index so we know from
    where to look for data rows.
    """
    metadata = {}  # metadata found in file header

    for i, row in enumerate(table):
        if i >= data_start:
            break  # Do not look for header beyond where data already started
        lrow = row.lower()

        def get_entry(x):
            return x.split(":", 1)[-1].strip()  # part after colon

        # This if/elif/... aka switch/case cascade should ideally be solved
        # using a dictionary, however the individual cases are treated so
        # differently that a lot of manual adjustment is necessary.
        if "dasylab" in lrow:
            metadata["generated_by"] = row.strip()
        elif "aufgenommen" in lrow:
            date = dateutil.parser.parse(get_entry(row))
            metadata["date_recorded"] = tz.localize(date)
        elif "blocklaenge" in lrow:
            metadata["block_length"] = value_cleanup(get_entry(row))
        elif "delta" in lrow:
            metadata["delta/s"] = value_cleanup(get_entry(row))
        elif "kanalzahl" in lrow:
            metadata["channel_count"] = value_cleanup(get_entry(row))
        elif "oil" in lrow:
            metadata.setdefault("oils", []).append(get_entry(row))
        elif "elastomer" in lrow:
            metadata.setdefault("elastomers", []).append(get_entry(row))
        elif "welle" in lrow:
            metadata.setdefault("shafts", []).append(get_entry(row))
        elif "versuchsname" in lrow:
            metadata["name"] = get_entry(row)
        elif "versuchsstand" in lrow:
            metadata["station"] = value_cleanup(get_entry(row))
        elif "kalibriergew" in lrow:
            metadata.setdefault("cal_weights/kg", []).append(
                value_cleanup(get_entry(row)))
        elif "tariergew" in lrow:
            metadata.setdefault("tar_weights_frac", []).append(
                value_cleanup(get_entry(row))
                * 100 / 100 ** 2  # 0.0000, avoiding float arithmetic
            )

    # Call strftime three time so that .join()-delimiter also applies to them:
    metadata["experiment_id"] = "_".join(
        [metadata.get("date_recorded").strftime("%Y"),
         metadata.get("date_recorded").strftime("%m"),
         metadata.get("date_recorded").strftime("%d"),
         str(metadata.get("name")), "T" + str(metadata.get("station"))]
    )

    metadata["diameter/m"] = 0.04297  # meter; hardcoded, doesn't change (?)

    metadata["data_origin"] = table.name  # mainly for debugging
    return metadata


def csv_to_dataframe(table_file, table_data_start: int, table_delimiter: str):
    """
    Read in CSV; does not have to literally be a *.csv-file, just a text file
    with columns separated by some delimiter and of course some rows.
    Generating the DF, parsing the date and creating and index from it takes
    a lot of time. This is the script's bottleneck. It could be done
    differently, but this approach is very simple, robust (not hacky), easy to
    maintain and will stay valid for years to come.
    Once the index is built, our reward is that any operations based on it are
    incredibly fast (e.g. sorting and joining later on).
    """
    dataframe = pandas.read_csv(
        table_file,  # May take path or file handle
        header=table_data_start,  # Header row index, 0-indexed
        delimiter=table_delimiter,
        parse_dates={"Time": ["Datum", "Uhrzeit"]},  # For explicit errors
        infer_datetime_format=True,
        index_col="Time",  # Again, be explicit
        decimal=","  # German/European data
    )

    # Drop all NaN columns (they occur since our rows *end* on delimiter,
    # generating an extra empty column of NaNs)
    dataframe.dropna(
        how="all",  # only if all entries NaN
        axis="columns",  # Default is rows
        inplace=True  # No value returned
    )

    # We rely on proper numeric types in all columns for later calculations:
    for y in dataframe.columns:
        if not pandas.api.types.is_numeric_dtype(dataframe[y]):
            raise TypeError("Not all columns are numeric. Wrong delimiter?")
    return dataframe


# 'Global' variables, i.e. for all directories:
tz = pytz.timezone("Europe/Berlin")  # For localization of datetime
logging.info(f"Set timezone to {tz}.")

# A better approach for matching would be regexs
categories = {  # All expected categories of physical quantities
    "Temperature": {
        "unit": "degC",
        "cols": ["Wellentemp", "Fluidtemp", "T"],
        "symbol": "T"
    },
    "Torque": {
        "unit": "N*mm",
        "cols": ["Moment", "M"],
        "symbol": "M"
    },
    "Rot_Speed": {
        "unit": "rpm",  # unit without numberals: nicer
        "cols": ["n", "N"],
        "symbol": "n"
    },
    "Speed_Voltage": {  # ???
        "unit": "V",
        "cols": ["Drehzahl"],
        "symbol": "U_n"
    },
    "Line_Load": {
        "unit": "N/mm",
        "cols": ["Linienlast"],
        "symbol": "f"
    },
    "Heating_Spec": {
        "unit": "J/kg?",  # Joule per kilogram?
        "cols": ["Heizenergie_Spez"],
        "symbol": "q"
    },
    "Heating_Time": {
        "unit": "s?",  # seconds?
        "cols": ["Heizenergie_Zeit"],
        "symbol": "t_q"
    },
    "Valve_Voltage": {
        "unit": "V",
        "cols": ["Ventilspannung", "V"],
        "symbol": "U_V"
    },
    "COF": {  # coefficient of friction
        "unit": "1",
        "cols": ["my"],
        "symbol": "mu"  # can be mu or my; mu is clearer
    },
    "Tan_Vel": {  # tangential velocity
        "unit": "m/s",
        "cols": ["Umfangsg"],
        "symbol": "v_theta"  # theta for greek t(angential)
    },
    "Standard_Deviation": {  # only valid for torque in this form
        "unit": "N*mm",
        "cols": ["Standar"],  # misspelled as "Standaradabw" in some files
        "symbol": "SD_M"  # standard deviation
    },
    "Sta?": {
        "unit": "1",
        "cols": ["Sta1", "Sta2"],  # hacky, but matches "Standardabw" else
        "symbol": "STA"
    },
    "Rich?": {  # direction?
        "unit": "1",
        "cols": ["Rich"],
        "symbol": "RICH"
    },
    "U?": {
        "unit": "1",
        "cols": ["U"],
        "symbol": "U"
    }
}

categories = pandas.DataFrame(categories)  # nicer tabular __repr__/print etc.

# These are going to be plotted, if available:
desired_plot_cats = [  # keys for categories dictionary
    "Temperature",
    "Torque",
    "Rot_Speed",
    "Line_Load",
    "Tan_Vel",
    "Valve_Voltage",
    "Heating_Time",
    "Heating_Spec"
]

indices = {  # keys found in header columns are to be replaced by their values
    "welle": "W",
    "fluid": "F",
    "soll": "S",
    "ist": "ist",
    "out": "out",
    "max": "avmax",
    "min": "avmin"
}

delimiter = ";"  # Delimiter used in tables
logging.info(f"Set expected table delimiter to '{delimiter}'.")


def quick_compile(regex):
    """Wrapper for reoccurring regex compilation operation"""
    return re.compile(r"\w+" + regex + r"\w+", re.I)


file_patterns = {
    "minutes": quick_compile(r"_S\d\."),
    "seconds": quick_compile(r"_S\d_sek\."),
    "log": quick_compile(r"_LOGFILE\."),
    "heizung": quick_compile(r"Heizung")
}

ignored_patterns = [file_patterns[x] for x in ["log", "heizung"]]

# Files are saved in this subdirectory:
base_export_dir = Path("out")
try:
    base_export_dir.mkdir()
except FileExistsError:
    pass

for subdir in [x for x in Path("in").iterdir() if x.is_dir()]:
    # General export directory path mimics the current subdirectory we are in:
    export_subdir = base_export_dir.joinpath(subdir.parts[-1])
    try:
        export_subdir.mkdir()
    except FileExistsError:
        logging.warning(f"Path '{export_subdir}' already exists, skipping it.")
        continue

    logging.info(f"Starting work on subdirectory '{subdir.name}'.".upper())

    # Subdirectory for all files regarding further (manual) analysis.
    # Keep in subdirectory to maintain clear top-level.
    analysis_dir = export_subdir.joinpath("analysis")
    analysis_dir.mkdir()
    logging.info(f"Created new subdirectory '{analysis_dir}'.")

    # Variables local to each subdirectory:
    dfs = {  # dataframes for the different kinds of recorded data
        "minutes": [],
        "seconds": []
    }

    got_metadata = False  # Acquire metadata once for each experiment/subdir

    for file in subdir.iterdir():
        # Only work on files with our specified file extension:
        if not re.match(r"(?i).+\.asc", file.name):
            logging.warning(
                f"File will be ignored (file suffix): {file.name}.")
            continue
        # Happens if file is open in other program. It can then still be
        # read here, but might be written to be the other program (Excel, ...).
        # Therefore, ignore 'locked' files:
        elif "lock" in file.name.lower():
            logging.warning(f"File will be ignored (locked): {file.name}.")
            continue
        # Check if any of the patterns we introduced matches:
        elif any([x.match(file.name) for x in ignored_patterns]):
            logging.warning(f"File will be ignored (pattern): {file.name}.")
            continue

        logging.info(f"Starting work on file '{file.name}'.".upper())

        # Get header row aka data start. This runs once for each file,
        # even if they share the same data start column (safe approach)
        with open(file) as spreadsheet:
            for table_index, row_content in enumerate(spreadsheet):
                lrow = row_content.lower()
                # Find column header row/data start based on these criteria:
                if "datum" in lrow and lrow.count(delimiter) > 1:
                    logging.info("Found the column header in row "
                                 f"{table_index + 1}.")
                    # Dismiss remaining rows after header.
                    # At this point, table_index corresponds to the row
                    # index where data starts/column header is found.
                    break

        # After filtering out the unwanted files, we must have found a
        # proper one. Turn it into a new dataframe:
        logging.info(f"Turning file '{file.name}' into pandas dataframe.")
        new_df = csv_to_dataframe(file, table_index, delimiter)
        logging.info(f"Turned file '{file.name}' into pandas dataframe.")

        # Now go through our time_types to see what type the found file
        # belongs to:
        for time_type in dfs:
            # Check if it is actually a match, so that 'minutes' is not
            # confused for 'seconds' data etc.:
            if file_patterns[time_type].match(file.name):
                # Find the metadata, but only once. For this, set flag
                # once we are done. Do this only after a match has occurred,
                # else we might be working on an illegitimate file.
                if time_type is "minutes" and not got_metadata:
                    with open(file) as spreadsheet:
                        logging.info("Collecting metadata from "
                                     f"file '{file.name}'.")
                        metadata = get_metadata(spreadsheet, table_index)
                        logging.info(f"Collected metadata from "
                                     f"file '{file.name}'.")
                    # Owed to this flag, this if-block is never entered again:
                    got_metadata = True
                # Now, go through the dataframes we have already collected in
                # our dictionary. Do this for the current time type.
                # If there is any intersection, i.e. common column names,
                # between one of the already existing dataframes for this time
                # type, and the newly added one, it is concluded that these
                # have the save column names. Therefore, they are concatenated
                # (vertically). This corresponds to finding a "_zwei_" file.
                # Such concatenation with .concat() is joined as 'outer' per
                # default so we lose no data and NaNs show up if something went
                # wrong.
                # If no such match in any column names is found (reached the
                # end of the iteration), there is no such category existing yet,
                # so we append it using 'else' of the for-loop.
                # Since the dfs dictionary is empty when we start, the
                # iteratin immediately hits the 'else' block as well and the
                # first value is appended.
                # This procedure means that we simply concatenate all dataframes
                # with the same (more precisely, similar) column names: we
                # do not have to care for treating '_zwei_' files specially.
                for i, existing_df in enumerate(dfs[time_type]):
                    if any(new_df.columns.intersection(existing_df.columns)):
                        logging.info("The new dataframe has at least one "
                                     "column in common with an already existing"
                                     f" dataframe for '{time_type}' data: "
                                     "concatenating the two.")
                        dfs[time_type][i] = pandas.concat(
                            [dfs[time_type][i], new_df])
                        break
                else:
                    logging.info("The new dataframe seems unique "
                                 "(no overlap in column names with existing "
                                 f"dataframes for '{time_type}' data): "
                                 "appending it.")
                    dfs[time_type].append(new_df)
                # If we entered this block, some match must have occurred.
                # Therefore, break out so we do not hit the 'else' block that
                # catches any file that fell through.
                break
        else:
            logging.warning(f"File was ignored (fell through): {file.name}.")

    for time_type in dfs:
        logging.info(f"Starting processing of '{time_type}' data.".upper())

        if all(x is None for x in dfs[time_type]):
            logging.warning(f"No data found for '{time_type}', skipping it.")
            continue
        # For each, join all dataframe-parts found in the list.
        # Join the first element with all subsequent ones, then override
        # so we release memory.
        # Join "outer" SQL-style so no data is lost and we detect errors
        # (by seeing NaNs).
        logging.info(f"Joining dataframes for '{time_type}'.")
        dfs[time_type] = dfs[time_type][0].join(
            dfs[time_type][1:], how="outer")
        logging.info(f"Joined dataframes for '{time_type}'.")

        # Currently, all files are named correctly, i.e. they are found and
        # processed by the script in their natural order anyway. That way, any
        # processing (mainly concatenation) works out of the box and yields
        # strictly ascending date-time in the index column. Should this ever not
        # be the case, sort the already built index here:
        logging.info(f"Sorting dataframe by index for '{time_type}'.")
        dfs[time_type].sort_index(inplace=True)
        logging.info(f"Sorted dataframe by index for '{time_type}'.")

        # Get tangential velocity from nN_iI(st_Antriebsmotor) columns.
        # Different cases occur, filter with regex.
        logging.info(f"Calculating additional columns for '{time_type}'.")
        dfs[time_type]["Umfangsg. [m/s]"] = dfs[time_type].filter(
            regex=r"(?i)n_i\w+").multiply(math.pi * metadata["diameter/m"] / 60)
        logging.info(f"Calculated additional columns for '{time_type}'.")

        category_col = []  # New column header for physical quantity *category*
        symbol_col = []  # New column header for phys. symbol, replacing old one

        # Hack required to fit into below scheme, where we test if column names
        # *start* with any string from a tuple.
        # Rename does not do anything if column not found.
        dfs[time_type].rename(
            columns={"M1_sigma []": "Standardabw M1"},
            inplace=True
        )

        for col_name in dfs[time_type].columns.to_list():
            logging.info(f"Working on column '{col_name}' for '{time_type}'.")
            # each category of phys. quantities and its attributes (units, ...)
            for cat, cat_attr in categories.items():
                possible_cols = cat_attr["cols"]  # possibilities to match for
                symbol = cat_attr["symbol"]  # physical symbol
                unit = cat_attr["unit"]

                # Note tuple v. list: tuple matches any
                if col_name.startswith(tuple(possible_cols)):
                    category_col.append(f"{cat}")  # /{unit}")
                    logging.info(f"Assigned category '{cat}' "
                                 f"to column '{col_name}'.")

                    # Index for the physical symbol.
                    # Initialize and let them fall through as None
                    # if not changed; None is filtered out later:
                    idx_abbr = None
                    idx_no = None

                    # Try to assign an index name:
                    for k, abbreviation in indices.items():
                        if k in col_name.lower():
                            idx_abbr = abbreviation
                            break

                    # A bit hacky; *exclude* this unit from digit search:
                    if not "[min-1]" in col_name.lower():
                        try:
                            # Fails if no match found:
                            # NoneType has no group() method.
                            # Else, extracts matching string through group(0)
                            idx_no = re.search(r"\d", col_name).group(0)
                        except AttributeError:
                            logging.warning(f"No index number found "
                                            f"for column '{col_name}'.")
                            # pass: idx_no stays as initialized above

                    # Omit underscore separation if symbol already includes one:
                    symbol_sep = "_" if "_" not in symbol else None

                    # Join symbol + all filtered (None thrown out) parts:
                    symbol_col.append(symbol +
                                      "".join(
                                          filter(None,
                                                 (symbol_sep, idx_abbr, idx_no)
                                                 )
                                      )
                                      )
                    logging.info(f"Renamed column '{col_name}' "
                                 f"to '{symbol_col[-1]}'.")
                    break  # Match found, leave
            else:  # When no match found, aka no 'break' occurred
                category_col.append("Other")
                symbol_col.append("??")
                logging.warning(f"No category or symbol found "
                                f"for column '{col_name}'.")

        # Replace single header row with two new ones as two lists:
        # [[category1, category2, category1, category1, category3, ...],
        # [symbol1, symbol2, symbol3, symbol3, symbol4, ...]], e.g.:
        # [["Temperature", "Torque", ...], ["T_1", "M_2", ...]]
        # Two column header rows (MultiIndex):
        dfs[time_type].columns = [category_col, symbol_col]
        # Names of these header rows:
        dfs[time_type].columns.names = ["Category", "Symbol"]
        logging.info(f"Renamed column headers for '{time_type}'.")

        # Construct path for CSV from current export directory path:
        csv_path = export_subdir.joinpath(time_type + ".csv")
        # %g: signif. digits
        dfs[time_type].to_csv(csv_path, float_format="%g")
        logging.info(f"Saved time type '{time_type}' to '{csv_path}'.")

        if time_type is "minutes":
            logging.info(f"Processing tasks specific to '{time_type}'.")
            # E.g. if we plot the "Torque" category, all average/min/max columns
            # are included; these should be left out.
            dfs[time_type].drop(  # Drop (probably) unwanted stuff
                columns=list(dfs[time_type].filter(  # Filter on columns
                    regex=r"\w+avm\w+")),  # filter out avmin and avmax columns
                inplace=True  # no return
            )
            logging.info(f"Dropped unwanted columns (for plotting) "
                         f"from '{time_type}' data.")

            # If desired plot category not in available column categories,
            # leave out:
            available_plot_cats = []
            for desired_plot_cat in desired_plot_cats:
                for available_category in dfs[time_type].columns.levels[0]:
                    if desired_plot_cat in available_category:
                        available_plot_cats.append(desired_plot_cat)

            logging.info(f"Desired categories to be plotted "
                         f"are: {desired_plot_cats}.")
            if available_plot_cats == desired_plot_cats:
                logging.info("All desired plot categories are available "
                             "and will be plotted.")
            else:
                unavailable_plots = [
                    x for x in desired_plot_cats
                    if x not in available_plot_cats
                ]
                logging.warning("The following desired plots are unavailable "
                                "in the data and will not be contained "
                                f"in the plots: {unavailable_plots}.")

            # Prepare a title for the plots with all important metadata:
            overview = [" + ".join(metadata.get(x))
                        for x in ["oils", "elastomers", "shafts"]]

            # Using f-strings with either \n or triple-quotation marks
            # gave me trouble, so resorted to format() method here:
            plot_title = "{title} \n [{subtitle}]".format(
                title=metadata.get("experiment_id"),
                subtitle=" / ".join(overview)
            )

            pdffile_path = export_subdir.joinpath("overview.pdf")
            with PdfPages(pdffile_path) as pdf:
                # Prepare (sub)figure and axes environments with 1 column
                # and as many rows/subplots as there are actual plots:
                subfig, subaxs = plt.subplots(
                    len(available_plot_cats),  # rows in the subplot
                    1,  # columns in the subplot
                    sharex='col'  # display x-axis only at very bottom
                )
                subfig.set_size_inches(8.27, 11.69)  # A4 paper in portrait
                plt.subplots_adjust(hspace=0.5)  # default: 0.2
                subfig.suptitle(plot_title)  # title for entire fig (not axes)

                # Loop over all plots and add to subfigure environment:
                for ax_no, available_plot_cat in enumerate(available_plot_cats):
                    # axes obj. already generated, use it for subplot:
                    dfs[time_type][available_plot_cat].plot(ax=subaxs[ax_no])
                    subaxs[ax_no].set_ylabel(
                        categories[available_plot_cat]["symbol"] + " / " +
                        categories[available_plot_cat]["unit"]
                    )
                    subaxs[ax_no].grid(linestyle=":")
                    subaxs[ax_no].legend(
                        bbox_to_anchor=(0.5, 1),  # Hor. middle, above plot
                        loc="lower center",  # legend anchor
                        ncol=99  # high number, forcing single-row legend
                    )

                pdf.savefig(subfig)  # Save generated figure with all subplots
                logging.info(f"Saved overview subfigures-plot to PDF file.")

                # Almost same loop again. Required since we want to save subfig
                # first, so it shows up on the first page. All the next plots
                # are full-page individual plots, each appended
                # (savefig() in loop) to pdf.
                for available_plot_cat in available_plot_cats:
                    fullaxs = dfs[time_type][available_plot_cat].plot(
                        figsize=(11.69, 8.27),  # A4 in landscape
                        title=plot_title
                    )
                    fullaxs.set_ylabel(
                        available_plot_cat + " / " +
                        categories[available_plot_cat]["unit"]
                    )
                    fullaxs.grid(linestyle=":")

                    # in loop: save once aka one page for each iteration:
                    pdf.savefig()
                    logging.info("Saved full-size plot for category "
                                 f"'{available_plot_cat}' to PDF file.")

                # PDF Metadata:
                d = pdf.infodict()
                d["Title"] = plot_title
                d["Author"] = "Gerrit Weiser"
                d["Subject"] = "Tribometer Evaluation"
                d["Keywords"] = ", ".join(metadata["experiment_id"].split("_"))
                d["ModDate"] = datetime.now()
                logging.info("Set PDF metadata.")

            logging.info(f"Saved PDF to '{pdffile_path}'.")

        elif time_type is "seconds":
            logging.info(f"Processing tasks specific to '{time_type}'.")
            # 'minutes' data is already averaged,
            # therefore get summary from raw 'seconds' data:
            summaryfile_path = export_subdir.joinpath("summary.csv")
            dfs[time_type].describe().to_csv(
                summaryfile_path,
                float_format="%g"
            )
            logging.info(f"Saved summary file to '{summaryfile_path}'.")
        else:
            raise KeyError(f"Got unexpected data '{time_type}'.")

    logging.info("Starting work on auxiliary tasks.")
    # figures created through pyplot are kept in memory until closed explicitly.
    # After they are saved as PDF for each subdirectory (i.e., experiment),
    # delete all references to figure objects by closing "all", so they may be
    # garbage-collected by Python.
    plt.close("all")

    # Datetime object requires string representation for JSON serialization:
    metadata["date_recorded"] = metadata["date_recorded"].isoformat(" ")

    metadata_path = export_subdir.joinpath("metadata.json")
    metadata_path.write_text(
        json.dumps(
            metadata,  # dictionary to JSON to string
            indent=4,
            sort_keys=True,  # so that dict keys aren't in random order
            ensure_ascii=False  # don't escape UTF-8 but print it
        )
    )
    logging.info(f"Saved metadata file to '{metadata_path}'.")
    logging.info(f"Successfully processed subdirectory '{subdir}'.")
