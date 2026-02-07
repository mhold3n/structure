import os
import hashlib
import glob
import json
from typing import Set


def get_file_hashes(directory: str) -> Set[str]:
    """
    Computes MD5 hashes of all file contents in a directory.
    Assumes files are text or JSON.
    """
    hashes = set()
    if not os.path.exists(directory):
        return hashes

    for filepath in glob.glob(os.path.join(directory, "**/*"), recursive=True):
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                hashes.add(file_hash)
    return hashes


def check_contamination():
    """
    Checks for contamination between Train/Dev and Test.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../indexes"))

    train_dir = os.path.join(base_dir, "train")
    dev_dir = os.path.join(base_dir, "dev")
    test_dir = os.path.join(base_dir, "test")

    print("Computing hashes for Test set...")
    test_hashes = get_file_hashes(test_dir)
    if not test_hashes:
        print("Test set is empty. No contamination possible (but also no test coverage!).")
        return

    print(f"Test set has {len(test_hashes)} unique files.")

    print("Checking Train set...")
    train_hashes = get_file_hashes(train_dir)
    train_overlap = train_hashes.intersection(test_hashes)

    print("Checking Dev set...")
    dev_hashes = get_file_hashes(dev_dir)
    dev_overlap = dev_hashes.intersection(test_hashes)

    if train_overlap:
        print(f"CRITICAL: {len(train_overlap)} files found in both Train and Test!")
        exit(1)

    if dev_overlap:
        print(f"CRITICAL: {len(dev_overlap)} files found in both Dev and Test!")
        exit(1)

    print("SUCCESS: No contamination detected.")


if __name__ == "__main__":
    check_contamination()
