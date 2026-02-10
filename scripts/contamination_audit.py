import os
import hashlib
import glob
import re
from typing import Set, Dict, List

# Constants for MinHash
NUM_HASHES = 100
HASH_SEEDS = [i * 1337 for i in range(NUM_HASHES)]


def get_shingles(text: str, k: int = 3) -> Set[str]:
    """Generate k-shingles (n-grams) from text."""
    text = re.sub(r"\s+", " ", text.strip().lower())
    if len(text) < k:
        return {text}
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def compute_minhash(text: str) -> List[int]:
    """Compute MinHash signature for text."""
    shingles = get_shingles(text)
    signature = []
    
    for seed in HASH_SEEDS:
        min_hash = float("inf")
        for shingle in shingles:
            # Simple combined hash
            h = hashlib.md5(f"{seed}_{shingle}".encode()).hexdigest()
            h_int = int(h, 16)
            if h_int < min_hash:
                min_hash = h_int
        signature.append(min_hash)
    
    return signature


def compute_jaccard_similarity(sig1: List[int], sig2: List[int]) -> float:
    """Estimate Jaccard similarity from MinHash signatures."""
    matches = sum(1 for h1, h2 in zip(sig1, sig2) if h1 == h2)
    return matches / len(sig1)


def load_file_signatures(directory: str) -> Dict[str, List[int]]:
    """
    Computes MinHash signatures of all file contents in a directory.
    """
    signatures = {}
    if not os.path.exists(directory):
        return signatures

    for filepath in glob.glob(os.path.join(directory, "**/*"), recursive=True):
        if os.path.isfile(filepath) and filepath.endswith(".json"): # Assuming JSON content for documents
            try:
                with open(filepath, "r") as f:
                    # Ingested documents are JSON with a "content" field
                    data = json.load(f)
                    content = data.get("content", "")
                    if content:
                        signatures[filepath] = compute_minhash(content)
            except Exception:
                pass
    return signatures


def check_contamination():
    """
    Checks for contamination between Train/Dev and Test using MinHash.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../indexes"))

    train_dir = os.path.join(base_dir, "train/documents")
    dev_dir = os.path.join(base_dir, "dev/documents")
    test_dir = os.path.join(base_dir, "test/documents")

    print("[*] Computing signatures for Test set...")
    test_sigs = load_file_signatures(test_dir)
    if not test_sigs:
        print("Test set is empty. No contamination possible.")
        return

    print(f"Test set has {len(test_sigs)} unique files.")

    print("[*] Checking Train set...")
    train_sigs = load_file_signatures(train_dir)
    check_overlap(train_sigs, test_sigs, "Train")

    print("[*] Checking Dev set...")
    dev_sigs = load_file_signatures(dev_dir)
    check_overlap(dev_sigs, test_sigs, "Dev")


def check_overlap(source_sigs: Dict[str, List[int]], target_sigs: Dict[str, List[int]], name: str):
    threshold = 0.8 # Jaccard similarity threshold for "near duplicate"
    violations = 0
    
    for s_path, s_sig in source_sigs.items():
        for t_path, t_sig in target_sigs.items():
            sim = compute_jaccard_similarity(s_sig, t_sig)
            if sim > threshold:
                print(f"CRITICAL: Potential contamination in {name}!")
                print(f"  Source: {s_path}")
                print(f"  Target: {t_path}")
                print(f"  Similarity: {sim:.2f}")
                violations += 1
                
    if violations == 0:
        print(f"SUCCESS: No near-duplicates found in {name}.")
    else:
        print(f"WARNING: Found {violations} potential contamination cases in {name}.")

if __name__ == "__main__":
    check_contamination()
