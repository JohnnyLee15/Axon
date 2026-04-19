from datasketch import MinHash
import xxhash
import numpy as np
from config import *

class MinHasher:
    # uint64 -> signed int 64
    def _u64_to_s64(self, val: int) -> int:
        return val if val < (1 << 63) else val - (1 << 64)


    def minhash_doc(self, doc: str) -> tuple[bytes | None, list[int] | None]:
        doc = NORMALIZE_DOC_PATTERN.sub("", doc.lower())
        if len(doc) < NUM_CHARS_PER_SHINGLE:
            return None, None

        minhash = MinHash(num_perm=NUM_MIN_HASH_FUNCS, seed=MIN_HASH_SEED)
        for i in range(len(doc) - NUM_CHARS_PER_SHINGLE + 1):
            shingle = doc[i:(i + NUM_CHARS_PER_SHINGLE)]
            minhash.update(shingle.encode("utf-8"))

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