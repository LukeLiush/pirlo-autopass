from unittest.mock import AsyncMock, MagicMock

import pytest

from pirlo.playbooks.autopass.core.use_cases import RunAutopassUseCase, slugify
from pirlo.playbooks.autopass.main import QuickProgressListener


def test_quick_progress_listener_status_context():
    listener = QuickProgressListener()
    # Ensure status_context works as a context manager without raising AttributeError
    with listener.status_context("Testing status context..."):
        assert True
    # Test show methods
    listener.show_warning("Test warning")
    listener.show_goal("Test goal", detail="Detail goal")
    listener.show_red_card("Test red card", detail="Detail error")


def test_slugify_task_prompt():
    assert (
        slugify("Go to google.com and search for OpenAI!")
        == "go_to_googlecom_and_search_for_open_931edcb9"
    )
    assert (
        slugify("   Navigate to github.com / trending   ")
        == "navigate_to_githubcom_trending_feb2e89f"
    )


from contextlib import asynccontextmanager


@pytest.mark.anyio
async def test_run_autopass_use_case_cache_key():
    mock_page = MagicMock()
    mock_browser_manager = MagicMock()

    @asynccontextmanager
    async def fake_new_page():
        yield mock_page

    mock_browser_manager.new_page = fake_new_page

    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(
        side_effect=lambda task_prompt, context=None: (
            f"result_for_{context.cache_key}" if context else "result"
        )
    )

    use_case = RunAutopassUseCase(
        workflow_runner=mock_runner,
    )

    listener = QuickProgressListener()
    res = await use_case.run(
        browser_manager=mock_browser_manager,
        task_prompt="Search OpenAI on Google",
        listener=listener,
        run_name="run123",
        run_id="id123",
    )

    assert res == "result_for_run123_search_openai_on_google_8b57355d"
