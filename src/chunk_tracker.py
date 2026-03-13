class ChunkTracker:
    def __init__(self):
        self._chunks = {}
        self._curr_chunk= ""
        self._curr_id = 0

    def add_text(self, next_text):
        if not next_text:
            return

        self._curr_chunk += next_text

    def flush(self):
        if self._curr_chunk:
            self._chunks[self._curr_id] = self._curr_chunk
            self._curr_chunk = ""
            self._curr_id += 1

    def curr_len(self):
        return len(self._curr_chunk)

    def get_chunks(self):
        return self._chunks

