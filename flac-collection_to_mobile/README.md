# Convert collection of FLAC files to mobile-friendly format

Spotify, YouTube *etc.* are annoying.
But any local, conventional music archive (that is, with lossless compressed or uncompressed files) very quickly grows too large for mobile devices.
To have the entire personal music collection on a phone requires some converting.
This is easily done, but this script tries to be a bit smarter about it:

* skips existing files
* just copies over already existing `mp3`s
* copies over cover images that are found as raster images
* traverses the input directory structure recursively and just mirrors it over to the export
* also preserves most/all metadata, something [`ffmpeg` does by default](https://stackoverflow.com/questions/26109837/convert-flac-to-mp3-with-ffmpeg-keeping-all-metadata#comment68867375_26109838), but its Python wrapper we use here (`pydub`) apparently struggles with (per default at least).
* the user can give a list of file formats that are to be converted, *e.g.* `flac`, `wav`, ...

The target file format aka extension is also hard-coded into the script, not that it matters.
Currently, this is `mp3` at the default bitrate of 128k.
That seems pretty low, but gives nice and compact files; chances are the difference will never be relevant on mobile headphones, especially in-ears.

## Usage

To use this script, one possibility is to create a symlink.
I am a `bash`/Linux beginner, so this will be basic and mainly a personal memory aid.
The directory `/usr/local/bin` should be on the `$PATH`:

```bash
echo $PATH
```

In it, create a symbolic link to this script:

```bash
ln -s /path/to/this/script /usr/local/bin/music_to_mobile
```

The script will put stuff into a default folder if called without a command-line argument.
Currently, this is `~/Music_Export`, aka a subdirectory in the user home folder.
This should be OS-agnostic.
Other parts aren't as easy on Windows;
for example, you would need `ffmpeg`.

With the link, `cd` into the directory your new, small music library should reside in.
Plugging in the Android phone (tested with a OnePlus 3T), it is mounted properly as `Android`, but shows up empty (in the Nautilus file browser at least), even after specifying `File Transfer` as the USB mode in the phone.
Putting that to `PTP` (something about picture transfer) and then just back to `File Transfer` fixed this (quite randomly) in my case.

Browse to the internal storage `Music` folder (or wherever else you'd like to put your converted stuff) and call

```bash
music_to_mobile .
```

The terminal line could look like

```bash
user@user-compooper:/run/user/1000/gvfs/mtp:host=Android_Android_7d66cf33/Internal shared storage/Music$ music_to_mobile .
```

The script will then work on the current folder (`.`) and also place its log file there, which can be freely removed.

Note that the script expects your music source to be `~/Music`.
