from __future__ import annotations

import logging
from typing import Any

from pirlo.core.models.actions import DoneAction
from pirlo.core.models.browser_config import BrowserConfig
from pirlo.core.models.execution_context import DEFAULT_CONTEXT, ExecutionContext
from pirlo.core.models.workflow import Workflow
from pirlo.core.repository.workflow_repository import WorkflowRepository
from pirlo.core.services.workflow_runner import WorkflowRunner
from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import BrowserContext as PlaywrightContext
from playwright.async_api import Page as PlaywrightPage
from playwright.async_api import async_playwright

from .adapter import PlaywrightAdapter

logger = logging.getLogger(__name__)


class PlaywrightReplayRunner(WorkflowRunner[PlaywrightPage]):
    """Executes a cached domain Workflow sequence deterministically using Playwright in pirlo-autopass."""

    def __init__(
        self,
        repository: WorkflowRepository,
        browser_config: BrowserConfig | None = None,
    ) -> None:
        self.repository = repository
        self.browser_config = browser_config or BrowserConfig()

    async def run(
        self,
        task_prompt: str,
        context: ExecutionContext[PlaywrightPage] = DEFAULT_CONTEXT,
    ) -> str:
        page = context.page
        workflow_id = context.cache_key
        run_id = context.run_id

        if not workflow_id:
            raise ValueError("cache_key (workflow_id) is required for replay.")
        workflow: Workflow = self.repository.load(workflow_id)

        if run_id and hasattr(self.repository, "directory"):
            run_dir = self.repository.directory / run_id
            try:
                run_dir.mkdir(parents=True, exist_ok=True)
                snapshot = run_dir / f"{workflow_id}_workflow.json"
                snapshot.write_text(
                    workflow.model_dump_json(indent=2), encoding="utf-8"
                )
            except Exception as e:
                logger.warning(f"Failed to snapshot workflow: {e}")

        async def on_step_update(step_num: int, action: Any) -> None:
            self.repository.save(workflow)

        if page is not None:
            adapter = PlaywrightAdapter(page)
            await adapter.execute_workflow(workflow, on_step_update=on_step_update)
        else:
            async with async_playwright() as p:
                if self.browser_config.cdp_url:
                    browser: PlaywrightBrowser = await p.chromium.connect_over_cdp(
                        self.browser_config.cdp_url
                    )
                    pw_context: PlaywrightContext = browser.contexts[0]
                    target_page: PlaywrightPage = (
                        pw_context.pages[0]
                        if pw_context.pages
                        else await pw_context.new_page()
                    )
                else:
                    browser = await p.chromium.launch(
                        headless=self.browser_config.headless
                    )
                    pw_context = await browser.new_context()
                    target_page = await pw_context.new_page()

                adapter = PlaywrightAdapter(target_page)
                await adapter.execute_workflow(workflow, on_step_update=on_step_update)
                if not self.browser_config.cdp_url:
                    await browser.close()

        final_action = workflow.actions[-1]
        if isinstance(final_action, DoneAction):
            return final_action.text
        return "Workflow completed."
