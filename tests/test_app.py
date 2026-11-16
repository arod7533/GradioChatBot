"""UI adapter tests: tool activity is visible without exposing model reasoning."""

import unittest
from unittest.mock import patch

from app import respond


class AppTests(unittest.TestCase):
    @patch("app.chat")
    def test_tool_step_is_collapsible_and_final_answer_updates(self, agent):
        agent.return_value = iter(
            [
                (
                    "tool",
                    {
                        "name": "search_flights",
                        "result": {"count": 2, "flights": []},
                    },
                ),
                ("answer", "Two"),
                ("answer", "Two flights"),
            ]
        )
        frames = list(respond("Find flights", []))
        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0][0].metadata["title"], "✓ Flight search")
        self.assertEqual(frames[0][0].metadata["status"], "done")
        self.assertEqual(len(frames[-1]), 2)
        self.assertEqual(frames[-1][-1].content, "Two flights")
        agent.assert_called_once_with("Find flights", [])


if __name__ == "__main__":
    unittest.main()
