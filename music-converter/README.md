# Convert collection of FLAC etc. files to mobile-friendly format

Spotify, YouTube *etc.* are annoying.
But any local, conventional music archive (that is, with lossless compressed or uncompressed files) very quickly grows too large for mobile devices.
To have the entire personal music collection on a phone requires some converting.
This is easily done, but this script tries to be a bit smarter about it:

* skips existing files
* just copies over already existing `mp3`s
* copies over cover images that are found as raster images
* embeds found cover images into the music files themselves
* traverses the input directory structure recursively and just mirrors it over to the export
* also preserves most/all metadata, something [`ffmpeg` does by default](https://stackoverflow.com/questions/26109837/convert-flac-to-mp3-with-ffmpeg-keeping-all-metadata#comment68867375_26109838), but its Python wrapper we use here (`pydub`) apparently struggles with (per default at least).
* the user can give a list of file formats that are to be converted, *e.g.* `flac`, `wav` *etc.*, as well as a target file format and bitrate (*e.g.* `mp3`, `320`k)

## Usage

Find out more by executing the contained Python package as a module:

```bash
python -m music-converter -h
```

### Docker

Using the [Dockerfile](Dockerfile):

```bash
# Assuming a directory structure like:
$ tree
.
├── Dockerfile
├── in
│   ├── Artist_1
│   │   ├── Album_1
│   │   │   ├── Track_01.flac
│   │   │   └── Track_02.flac
│   │   └── Album_2
│   │       ├── Track_01.flac
│   │       └── Track_02.flac
│   └── Artist_2
│       ├── Album_1
│       │   ├── Track_01.flac
│       │   └── Track_02.flac
│       └── Album_2
│           ├── Track_01.flac
│           └── Track_02.flac
├── music-converter
│   └── __main__.py
├── out
├── README.md
└── requirements.txt

9 directories, 12 files

$ docker build . -t python:music-converter
$ docker run \
  # Remove container after successful run
  --rm \
  # Attach/print STDIN
  -it \
  # Run as current user/group, otherwise root:root owns your new files...
  --user=$UID:$GID \
  # Map input and output volumes
  --volume "$PWD"/in:/in \
  --volume "$PWD"/out:/out \
  python:music-converter \
  # Any further arguments
  -vv
```

The only important part is the correct mount point inside the container.
The origin music files can reside anywhere on your machine.
