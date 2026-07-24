class ContextBufferTracker:
    def __init__(self) -> None:
        self._context_buffers = []
        self._char_map_list = []
        self._curr_char_map = {}
        self._curr_buffer = ""


    def __len__(self) -> int:
        return len(self._curr_buffer)


    def add_chunk(self, text: str, cid: int) -> None:
        if not text:
            return

        start_idx = len(self._curr_buffer)
        self._curr_buffer += text
        end_idx = len(self._curr_buffer)
        self._curr_char_map[cid] = (start_idx, end_idx)


    def flush(self) -> None:
        if self._curr_buffer:
            self._context_buffers.append(self._curr_buffer)
            self._char_map_list.append(self._curr_char_map)
            self._curr_buffer = ""
            self._curr_char_map = {}


    def get_context_buffers(self) -> list[str]:
        return self._context_buffers


    def get_curr_buffer(self) -> str:
        return self._curr_buffer


    def get_char_map_list(self) -> list[dict[int, tuple[int, int]]]:
        return self._char_map_list

