import re

from datasketch import MinHash
import xxhash
import numpy as np


LSH_BAND_COUNT = 32
LSH_ROWS_PER_BAND = 8
NUM_MIN_HASH_FUNCS = LSH_BAND_COUNT * LSH_ROWS_PER_BAND
MINHASH_SEED = 16
NUM_CHARS_PER_SHINGLE = 5
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]")


class MinHasher:
    def _unsigned_to_signed_int64(self, val: int) -> int:
        return val if val < (1 << 63) else val - (1 << 64)


    def _hash_bands(self, minhash_signature: np.ndarray) -> list[int]:
        band_hashes = []
        for i in range(LSH_BAND_COUNT):
            start = i * LSH_ROWS_PER_BAND
            end = start + LSH_ROWS_PER_BAND
            band = minhash_signature[start:end]

            band_hash = xxhash.xxh64(band)
            band_hashes.append(self._unsigned_to_signed_int64(band_hash.intdigest()))

        return band_hashes


    def create_fingerprint(self, doc: str) -> tuple[bytes, list[int]] | None:
        normalized_doc = NON_ALPHANUMERIC_PATTERN.sub("", doc.lower())
        if len(normalized_doc) < NUM_CHARS_PER_SHINGLE:
            return None

        minhash = MinHash(num_perm=NUM_MIN_HASH_FUNCS, seed=MINHASH_SEED)
        num_shingles = len(normalized_doc) - NUM_CHARS_PER_SHINGLE + 1
        for i in range(num_shingles):
            shingle = normalized_doc[i:(i + NUM_CHARS_PER_SHINGLE)]
            minhash.update(shingle.encode("utf-8"))

        minhash_signature = minhash.digest()
        band_hashes = self._hash_bands(minhash_signature)

        return minhash_signature.tobytes(), band_hashes


    def estimate_jaccard(self, hash1: bytes, hash2: bytes) -> float:
        hash1_ints = np.frombuffer(hash1, dtype=np.uint64)
        hash2_ints = np.frombuffer(hash2, dtype=np.uint64)
        return np.mean(hash1_ints == hash2_ints)