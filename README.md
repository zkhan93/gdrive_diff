Script to compare files on Google Drive vs files on a local system
uses a App Script to get list of files from users Google Drive

It caches the file lists so that comparison code can be altered and rerun
```
Usage: main.py [OPTIONS]

Options:
  --gdrive-folder TEXT  Folder on GDrive  [required]
  --local-folder TEXT   Local folder  [required]
  --help                Show this message and exit.
```