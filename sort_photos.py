#!/usr/bin/env python3
"""Sort photos into YYYY_MM_DD folders by their creation date.

Uses the EXIF DateTimeOriginal tag when available (requires Pillow), and
falls back to the file's modification time otherwise.
"""

import shutil
from datetime import datetime
from pathlib import Path

import click

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
        click.echo(f"No photos found in {source}")
        return

    action = "Copy" if copy else "Move"
    moved = 0
    for path in files:
        folder = destination / creation_date(path).strftime("%Y_%m_%d")
        if dry_run:
            click.echo(f"{action} {path.name} -> {folder.name}/")
            continue

        folder.mkdir(parents=True, exist_ok=True)
        target = unique_destination(folder, path.name)
        if path.resolve() == target.resolve():
            continue
        if copy:
            shutil.copy2(path, target)
        else:
            shutil.move(str(path), str(target))
        click.echo(f"{path.name} -> {folder.name}/{target.name}")
        moved += 1

    if dry_run:
        click.echo(f"\nDry run: {len(files)} photo(s) would be sorted.")
    else:
        click.echo(f"\nDone: {moved} photo(s) sorted into {destination}")


@click.command(help=__doc__)
@click.argument("source", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-d", "--destination", type=click.Path(file_okay=False, path_type=Path),
              help="Where the date folders go  [default: the source folder]")
@click.option("-c", "--copy", is_flag=True, help="Copy instead of move.")
@click.option("-r", "--recursive", is_flag=True, help="Also scan subfolders.")
@click.option("-n", "--dry-run", is_flag=True,
              help="Show what would happen without touching any files.")
def main(source, destination, copy, recursive, dry_run):
    if Image is None:
        click.secho("note: Pillow not installed, using file modification times "
                    "(pip install Pillow for EXIF dates)\n", fg="yellow")

    sort_photos(source, destination or source,
                copy=copy, recursive=recursive, dry_run=dry_run)


if __name__ == "__main__":
    main()
