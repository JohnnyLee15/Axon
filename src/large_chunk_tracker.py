class LargeChunkTracker:
    def __init__(self):
        self._large_blocks = []
        self._char_map_list = []
        self._curr_char_map = {}
        self._curr_text = ""

    def add_text(self, text, bid):
        if not text:
            return

        start_idx = len(self._curr_text)
        self._curr_text += text
        end_idx = len(self._curr_text)

        if bid in self._curr_char_map:
            self._curr_char_map[bid] = (self._curr_char_map[bid][0], end_idx)
        else:
            self._curr_char_map[bid] = (start_idx, end_idx)

    def flush(self):
        if self._curr_text:
            self._large_blocks.append(self._curr_text)
            self._char_map_list.append(self._curr_char_map)
            self._curr_text = ""
            self._curr_char_map = {}

    def get_curr_text(self):
        return self._curr_text

    def get_large_blocks(self):
        return self._large_blocks

    def get_char_map_list(self):
        return self._char_map_list

