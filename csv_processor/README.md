# Experiment evaluation at M16

Home: <https://www.tuhh.de/mub/startseite.html>

## Structure

Execute this script one level above where all data-subdirectories sit.
The script traverses all subdirectories found in some specified input directory.
The names for the in- and output directories can be changed in the script.
The directory structure is:

___

- [`.gitignore`](.gitignore) *etc.*
- [`main script`](asc_to_csv.py)
- [`in`](in/)
  - subdir1 (experiment 1)
    - `a.asc` (plain file: treated as 'minutes' data)
    - `a_sek.asc` (`_sek.asc` suffix: 'seconds' data)
    - `b.asc`
    - `b_sek.asc`
    - `c.asc`
    - `c_sek.asc`
    - ... *etc.*
    - `a_zwei.asc` (concatenated to `a.asc`)
    - `a_zwei_sek.asc` (concatenated to `a_sek.asc`)
    - ... *etc.*
    - `x.m` (ignored)
    - `y.mat` (ignored)
    - `z.pdf` (ignored)
    - `*.png`, *etc.* (all ignored)
  - subdir2 (experiment 2)
    - same or similar to above
  - subdir3 (experiment 3)
    - ...
- ...
- `out`

___

It finds the relevant `asc` files and processes them.
The processed files are saved as `csv` to an output directory on the same level as the input directory.

It relies on the above structure; more nesting of directories breaks the scripts.
The contents are currently not traversed fully/recursively.

All 'seconds' and 'minutes' data is collected separately.
If dataframes (*ie.* tables) have columns in common, they are **concatenated**.
At the end, all 'seconds' and 'minutes' data is **joined**, again separately.
The join takes place on the index by default.
The index was set to the date-time on import.
That way, the joined 'seconds' and 'minutes' data only have one left-most date-time column (treated as the index in pandas).

Two large dataframes result, one for each time type.
Each is saved to its own `*.csv` file.
