import unittest
from unittest.mock import patch

from axon.ui.formatters import format_elapsed_time
from axon.ui.wait_status import WaitStatus


class WaitStatusTests(unittest.TestCase):
    def test_formats_seconds_minutes_and_hours(self) -> None:
        self.assertEqual(format_elapsed_time(12), "12s")
        self.assertEqual(format_elapsed_time(68), "1m 08s")
        self.assertEqual(format_elapsed_time(7_459), "2h 04m 19s")

    def test_renders_elapsed_time_without_cancel_hint(self) -> None:
        with patch("axon.ui.wait_status.time.monotonic") as monotonic:
            monotonic.return_value = 100.0
            status = WaitStatus(show_cancel_hint=False)
            monotonic.return_value = 112.9

            rendered = status.__rich__()

        self.assertEqual(rendered.plain, "Working (12s)")

    def test_renders_cancel_hint_when_enabled(self) -> None:
        with patch("axon.ui.wait_status.time.monotonic") as monotonic:
            monotonic.return_value = 100.0
            status = WaitStatus(show_cancel_hint=True)
            monotonic.return_value = 168.0

            rendered = status.__rich__()

        self.assertEqual(
            rendered.plain,
            "Working (1m 08s  •  Esc to interrupt)",
        )

    def test_uses_provided_start_time(self) -> None:
        with patch("axon.ui.wait_status.time.monotonic", return_value=112.9):
            status = WaitStatus(
                show_cancel_hint=False,
                started_at=100.0,
            )

            rendered = status.__rich__()

        self.assertEqual(rendered.plain, "Working (12s)")


if __name__ == "__main__":
    unittest.main()
