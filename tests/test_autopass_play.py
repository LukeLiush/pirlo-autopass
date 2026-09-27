import unittest

from pirlo_autopass.subplays import slugify


class TestAutopassPlay(unittest.TestCase):
    def test_slugify_task_prompt(self) -> None:
        self.assertEqual(
            slugify("Go to google.com and search for OpenAI!"),
            "go_to_googlecom_and_search_for_open_931edcb9",
        )
        self.assertEqual(
            slugify("   Navigate to github.com / trending   "),
            "navigate_to_githubcom_trending_feb2e89f",
        )


if __name__ == "__main__":
    unittest.main()
