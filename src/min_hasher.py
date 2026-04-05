from datasketch import MinHash
import xxhash
import numpy as np
from rich.console import Console
from config import *

class MinHasher:
    def __init__(self, console: Console) -> None:
        self._console = console

    # uint64 -> signed int 64
    def _u64_to_s64(self, val: int) -> int:
        return val if val < (1 << 63) else val - (1 << 64)


    def minhash_doc(self, doc: str) -> tuple[bytes | None, list[int] | None]:
        words = doc.split()
        if len(words) < NUM_WORDS_PER_ITEM:
            return None, None

        minhash = MinHash(num_perm=(LSH_BANDS * LSH_ROWS), seed=MIN_HASH_SEED)
        for i in range(len(words) - NUM_WORDS_PER_ITEM + 1):
            shingle = words[i:(i + NUM_WORDS_PER_ITEM)]
            shingle_bytes = " ".join(shingle).encode("utf-8")
            minhash.update(shingle_bytes)

        # dtype is uint64
        minhash_sig = minhash.digest()
        band_hashes = []
        for i in range(LSH_BANDS):
            start = i * LSH_ROWS
            end = start + LSH_ROWS
            band_slice = minhash_sig[start:end]
            band_hash = xxhash.xxh64(band_slice)
            band_hashes.append(self._u64_to_s64(band_hash.intdigest()))

        return minhash_sig.tobytes(), band_hashes


    def estimate_jaccard(self, hash1: bytes, hash2: bytes) -> float:
        hash1_ints = np.frombuffer(hash1, dtype=np.uint64)
        hash2_ints = np.frombuffer(hash2, dtype=np.uint64)
        return np.mean(hash1_ints == hash2_ints)