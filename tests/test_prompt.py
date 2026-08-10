import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from axon.ui.prompt import Prompt


class PromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_listen_builds_model_and_directory_status(self) -> None:
        prompt = Prompt.__new__(Prompt)
        prompt._input_session = Mock()
        prompt._input_session.prompt = AsyncMock(return_value="  hello  ")
        prompt._get_percentage_text = Mock(return_value="[10%]")
        prompt._get_display_cwd = Mock(return_value=Path("~/Axon"))

        result = await prompt.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self.assertEqual(result, "hello")
        self.assertEqual(
            prompt._input_session.prompt.await_args.kwargs["status_text"],
            "  gemini-test  •  ~/Axon",
        )


if __name__ == "__main__":
    unittest.main()
