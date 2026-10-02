#!/usr/bin/env python3
"""Sort photos into YYYY_MM_DD folders by their creation date.

Uses the EXIF DateTimeOriginal tag when available (requires Pillow), and
falls back to the file's modification time otherwise.
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".gif", ".webp"}

# EXIF tag ids: 36867 = DateTimeOriginal, 306 = DateTime
EXIF_DATE_TAGS = (36867, 306)


def exif_date(path):
    """Return the EXIF capture date, or None if unavailable."""
    if Image is None:
        return None
    try:
        with Image.open(path) as img:
            exif = img.getexif()
    except Exception:
        return None
    if not exif:
        return None
    for tag in EXIF_DATE_TAGS:
        value = exif.get(tag)
        if value:
            try:
                return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    return None


def creation_date(path):
    date = exif_date(path)
    if date is not None:
        return date
    return datetime.fromtimestamp(path.stat().st_mtime)


def unique_destination(folder, name):
    """Return a path in folder that does not collide with an existing file."""
    target = folder / name
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for i in range(1, 10000):
        candidate = folder / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"too many name collisions for {name}")


def sort_photos(source, destination, copy=False, recursive=False, dry_run=False):
    pattern = "**/*" if recursive else "*"
    files = sorted(p for p in source.glob(pattern)
                   if p.is_file() and p.suffix.lower() in EXTENSIONS)

    if not files:
        print(f"No photos found in {source}")
        return

    action = "Copy" if copy else "Move"
    moved = 0
    for path in files:
        folder = destination / creation_date(path).strftime("%Y_%m_%d")
        if dry_run:
            print(f"{action} {path.name} -> {folder.name}/")
            continue

        folder.mkdir(parents=True, exist_ok=True)
        target = unique_destination(folder, path.name)
        if path.resolve() == target.resolve():
            continue
        if copy:
            shutil.copy2(path, target)
        else:
            shutil.move(str(path), str(target))
        print(f"{path.name} -> {folder.name}/{target.name}")
        moved += 1

    if dry_run:
        print(f"\nDry run: {len(files)} photo(s) would be sorted.")
    else:
        print(f"\nDone: {moved} photo(s) sorted into {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="folder containing the photos")
    parser.add_argument("-d", "--destination", type=Path,
                        help="where the date folders go (default: the source folder)")
    parser.add_argument("-c", "--copy", action="store_true",
                        help="copy instead of move")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="also scan subfolders")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="show what would happen without touching any files")
    args = parser.parse_args()

    if not args.source.is_dir():
        sys.exit(f"error: {args.source} is not a directory")

    if Image is None:
        print("note: Pillow not installed, using file modification times "
              "(pip install Pillow for EXIF dates)\n")

    sort_photos(args.source, args.destination or args.source,
                copy=args.copy, recursive=args.recursive, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
