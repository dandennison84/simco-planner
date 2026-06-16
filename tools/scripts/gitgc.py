import os
from pathlib import Path

def remove_empty_dirs(root: Path):
    """
    Recursively remove empty directories under the given root.
    Walks bottom-up to ensure nested empty dirs are removed correctly.
    """
    # Walk bottom-up so children are processed before parents
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)

        # Skip the root itself (optional safety)
        if path == root:
            continue

        try:
            # If directory is empty after child cleanup, remove it
            if not any(path.iterdir()):
                path.rmdir()
                print(f"Removed empty directory: {path}")
        except Exception as e:
            print(f"Error removing {path}: {e}")


if __name__ == "__main__":
    git_objects = Path(".git/objects")

    if not git_objects.exists():
        print("Error: .git/objects directory not found")
    else:
        remove_empty_dirs(git_objects)