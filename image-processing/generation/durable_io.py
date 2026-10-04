"""Publish receipts and copied artifacts only after their bytes reach disk."""
import json
import os
from pathlib import Path
import shutil
import tempfile


def sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '.', delete=False) as stream:
            temporary = Path(stream.name)
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_json(path, value):
    data = (json.dumps(value, indent=2) + '\n').encode()
    _publish(path, lambda stream: stream.write(data))


def copy_file(source, target):
    if Path(source).resolve() == Path(target).resolve():
        return
    def write(stream):
        with open(source, 'rb') as original:
            shutil.copyfileobj(original, stream)
    _publish(target, write)


def sync_files(folder, names):
    for name in names:
        with (Path(folder) / name).open('rb') as stream:
            os.fsync(stream.fileno())
    sync_directory(folder)
