import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pirlo.core.models.actions import (
    ClickAction,
    DoneAction,
    ElementContext,
    NavigateAction,
)
from pirlo.core.models.browser_config import BrowserConfig
from pirlo.core.models.execution_context import ExecutionContext
from pirlo.core.models.workflow import Workflow
from pirlo.infrastructure.repository import JsonFileWorkflowRepository

from pirlo_autopass.adapters.playwright import (
    PlaywrightAdapter,
    PlaywrightReplayRunner,
)
from pirlo_autopass.adapters.workflow import SelfHealingRunner


class TestAutopassRunners(unittest.TestCase):
    def test_playwright_adapter_step_callback(self) -> None:
        actions = [
            NavigateAction(url="https://www.google.com"),
            ClickAction(
                element_context=ElementContext(
                    xpath="//button", tag_name="button", text="click me"
                )
            ),
        ]
        workflow = Workflow(
            workflow_id="dummy-flow",
            description="test description",
            actions=actions,
        )

        mock_page: AsyncMock = AsyncMock()
        mock_page.url = "https://www.google.com"
        mock_page.locator = MagicMock()

        mock_locator: AsyncMock = AsyncMock()
        mock_locator.scroll_into_view_if_needed = AsyncMock()
        mock_locator.evaluate = AsyncMock(
            side_effect=lambda js: "BUTTON" if "tagName" in js else {}
        )
        mock_locator.inner_text = AsyncMock(return_value="click me")
        mock_page.locator.return_value.first = mock_locator

        adapter: PlaywrightAdapter = PlaywrightAdapter(mock_page)
        adapter.execute_action = AsyncMock()

        called_steps: list[tuple[int, str]] = []

        async def on_step_update(step_num: int, action: object) -> None:
            called_steps.append((step_num, action.status.value))

        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()
        try:
            asyncio.run(
                adapter.execute_workflow(workflow, on_step_update=on_step_update)
            )
        finally:
            asyncio.sleep = original_sleep

        self.assertIn((1, "not_started"), called_steps)
        self.assertIn((2, "not_started"), called_steps)
        self.assertIn((1, "running"), called_steps)
        self.assertIn((1, "completed"), called_steps)
        self.assertIn((2, "running"), called_steps)
        self.assertIn((2, "completed"), called_steps)

    def test_workflow_runner_cache_key_and_step_history(self) -> None:
        cache_dir = Path(tempfile.mkdtemp())
        try:
            repo = JsonFileWorkflowRepository(directory=cache_dir)
            mock_replay = MagicMock()
            mock_replay.run = AsyncMock(return_value="replay result")
            mock_fallback = MagicMock()

            run_name = "regista-12345678"
            run_id = "regista-12345678-20260811_123456_000000"
            workflow = Workflow(
                workflow_id=run_name,
                description="test task",
                actions=[
                    NavigateAction(url="https://google.com"),
                    DoneAction(text="done"),
                ],
            )
            repo.save(workflow)

            runner = SelfHealingRunner(
                replay_runner=mock_replay,
                fallback_runner=mock_fallback,
                repository=repo,
            )

            result = asyncio.run(
                runner.run(
                    task_prompt="test prompt",
                    context=ExecutionContext(cache_key=run_name, run_id=run_id),
                )
            )
            self.assertEqual(result, "replay result")
            self.assertTrue(repo.exists(run_name))
        finally:
            import shutil

            shutil.rmtree(cache_dir)

    def test_playwright_replay_runner_snapshots_workflow_to_run_dir(
        self,
    ) -> None:
        cache_dir = Path(tempfile.mkdtemp())
        try:
            repo = JsonFileWorkflowRepository(directory=cache_dir)
            cache_key = "test_cache_key"
            run_id = "test_cache_key-20260811_123456_000000"
            wf = Workflow(
                workflow_id=cache_key,
                description="test task",
                actions=[
                    NavigateAction(url="https://example.com"),
                    DoneAction(text="done"),
                ],
            )
            repo.save(wf)

            runner = PlaywrightReplayRunner(
                repository=repo,
                browser_config=BrowserConfig(cdp_url=None),
            )

            with patch(
                "pirlo_autopass.adapters.playwright.runner.async_playwright"
            ) as mock_pw:
                mock_p = MagicMock()
                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()
                mock_browser.new_context.return_value = mock_context
                mock_context.new_page.return_value = mock_page
                mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_pw.return_value.__aenter__.return_value = mock_p

                with patch(
                    "pirlo_autopass.adapters.playwright.runner.PlaywrightAdapter.execute_workflow",
                    new_callable=AsyncMock,
                ):
                    asyncio.run(
                        runner.run(
                            task_prompt="test",
                            context=ExecutionContext(
                                cache_key=cache_key, run_id=run_id
                            ),
                        )
                    )

            snapshot_file = cache_dir / run_id / f"{cache_key}_workflow.json"
            self.assertTrue(snapshot_file.exists())
        finally:
            import shutil

            shutil.rmtree(cache_dir)


if __name__ == "__main__":
    unittest.main()
