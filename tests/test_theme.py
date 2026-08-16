import unittest
from unittest.mock import patch

from axon.ui import theme


class ThemeTests(unittest.TestCase):
    def test_detects_light_and_dark_ansi_backgrounds(self) -> None:
        self.assertTrue(theme._is_light_ansi_background("0;15"))
        self.assertFalse(theme._is_light_ansi_background("15;0"))

    def test_ignores_missing_or_unknown_ansi_backgrounds(self) -> None:
        self.assertIsNone(theme._is_light_ansi_background(None))
        self.assertIsNone(theme._is_light_ansi_background("invalid"))
        self.assertIsNone(theme._is_light_ansi_background("0;4"))

    def test_detects_light_and_dark_rgb_backgrounds(self) -> None:
        self.assertTrue(theme._is_light_rgb_background((255, 255, 255)))
        self.assertFalse(theme._is_light_rgb_background((0, 0, 0)))

    def test_ignores_unknown_terminal_background(self) -> None:
        self.assertIsNone(
            theme._is_light_rgb_background(
                theme.UNKNOWN_TERMINAL_BACKGROUND
            )
        )

    def test_queries_terminal_background_with_short_timeout(self) -> None:
        with patch("axon.ui.theme.Terminal") as terminal:
            terminal.return_value.get_bgcolor.return_value = (255, 255, 255)

            is_light_background = theme._is_light_terminal_background()

        self.assertTrue(is_light_background)
        terminal.return_value.get_bgcolor.assert_called_once_with(
            timeout=theme.TERMINAL_BACKGROUND_QUERY_TIMEOUT,
            bits=8,
        )

    def test_prefers_terminal_hint_over_terminal_query(self) -> None:
        with (
            patch.dict("axon.ui.theme.os.environ", {"COLORFGBG": "0;15"}),
            patch("axon.ui.theme._is_light_terminal_background") as query,
        ):
            background = theme.get_user_input_background()

        self.assertEqual(background, theme.USER_LIGHT_INPUT_BACKGROUND)
        query.assert_not_called()

    def test_uses_terminal_query_when_hint_is_missing(self) -> None:
        with (
            patch.dict("axon.ui.theme.os.environ", {}, clear=True),
            patch(
                "axon.ui.theme._is_light_terminal_background",
                return_value=False,
            ),
        ):
            background = theme.get_user_input_background()

        self.assertEqual(background, theme.USER_DARK_INPUT_BACKGROUND)

    def test_falls_back_to_default_background(self) -> None:
        with (
            patch.dict("axon.ui.theme.os.environ", {}, clear=True),
            patch(
                "axon.ui.theme._is_light_terminal_background",
                return_value=None,
            ),
        ):
            background = theme.get_user_input_background()

        self.assertEqual(background, theme.USER_DEFAULT_INPUT_BACKGROUND)


if __name__ == "__main__":
    unittest.main()
