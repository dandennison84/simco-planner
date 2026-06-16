import shutil
import os
from pathlib import Path
import stat

def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

objects_dir = Path(".git/objects")

for path in objects_dir.iterdir():
    if path.is_dir() and len(path.name) == 2:  # only fanout dirs like 00–ff
        try:
            shutil.rmtree(path, onerror=on_rm_error)
            print(f"Removed: {path}")
        except Exception as e:
            print(f"Error removing {path}: {e}")