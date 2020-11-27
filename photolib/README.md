# Simple tools to work with a photo collection

## ToDo

- [Add `xmp` to `mimetypes`](https://docs.python.org/3/library/mimetypes.html#mimetypes.add_type) and add corresponding method.
- Generally, add all mimetypes that could possibly be relevant.
- Add Rename facility for file extensions (make all lower- or uppercase)
- Add `classmethod` to read library from file `dump` (maybe use DB/JSON/...?)
- Add facility to check if *all* dates agree. For example, for a file
  `/pics/2020/01/01/2020-01-01_test-pics.arw`:
  - date in directory hierarchy matches
  - date in filename matches
  - date in EXIF/metadata
- Maybe play with metaclass to automatically generate `xyz_files` `property` objects that
  are called with `category=xyz` (duplication).
- Maybe add a stat overview for the library, requiring storing filesize etc. data.
  For this, maybe use [`rich`](https://github.com/willmcgugan/rich).
- Implement CLI (`rich`, `argparse`)
