import unittest
from unittest.mock import Mock

from axon.session.reference_presenter import ReferencePresenter
from axon.web_search.contracts import WEB_SOURCE_FIELDS


class WebSourcePresenterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ui = Mock()
        self.presenter = ReferencePresenter(
            paper_repository=Mock(),
            ui=self.ui,
        )

    def test_deduplicates_web_sources_by_url_in_original_order(self) -> None:
        first = {
            WEB_SOURCE_FIELDS.TITLE: "First title",
            WEB_SOURCE_FIELDS.URL: "https://example.com/first",
        }
        duplicate = {
            WEB_SOURCE_FIELDS.TITLE: "Alternate title",
            WEB_SOURCE_FIELDS.URL: "https://example.com/first",
        }
        second = {
            WEB_SOURCE_FIELDS.TITLE: "Second title",
            WEB_SOURCE_FIELDS.URL: "https://example.com/second",
        }

        self.presenter.display_web_sources([first, duplicate, second])

        self.ui.display_web_sources.assert_called_once_with([first, second])

    def test_does_not_render_empty_web_sources(self) -> None:
        self.presenter.display_web_sources([])

        self.ui.display_web_sources.assert_not_called()


if __name__ == "__main__":
    unittest.main()
