from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime

import httpx
from browser_use import BrowserSession
from browser_use.browser.events import SwitchTabEvent
from pirlo.core.models.browser_config import BrowserConfig
from pirlo.core.models.execution_context import DEFAULT_CONTEXT, ExecutionContext
from pirlo.core.models.workflow import WorkflowMetadata
from pirlo.core.repository.workflow_repository import WorkflowRepository
from pirlo.core.services.workflow_runner import WorkflowRunner
from playwright.async_api import Page as PlaywrightPage

from ..browser_agent.factory import BrowserAgentFactory
from .history_converter import convert_history_to_workflow

logger = logging.getLogger(__name__)


class LlmWorkflowRunner(WorkflowRunner[PlaywrightPage]):
    def __init__(
        self,
        agent_factory: BrowserAgentFactory,
        repository: WorkflowRepository,
        browser_config: BrowserConfig,
    ) -> None:
        self.agent_factory = agent_factory
        self.repository = repository
        self.browser_config = browser_config

    async def run(
        self,
        task_prompt: str,
        context: ExecutionContext[PlaywrightPage] = DEFAULT_CONTEXT,
    ) -> str:
        page = context.page
        if page is None or not self.browser_config.cdp_url:
            raise ValueError("LlmWorkflowRunner requires active page and CDP URL")
        workflow_id = (
            context.cache_key or hashlib.sha256(task_prompt.encode()).hexdigest()[:16]
        )

        browser = BrowserSession(
            cdp_url=self.browser_config.cdp_url,
            headless=self.browser_config.headless,
        )
        cdp = await page.context.new_cdp_session(page)
        info = await cdp.send("Target.getTargetInfo")
        target_id = info["targetInfo"]["targetId"]
        await cdp.detach()

        await browser.start()
        try:
            evt = browser.event_bus.dispatch(SwitchTabEvent(target_id=target_id))
            await evt
            agent = self.agent_factory.create_agent(task_prompt, browser=browser)
            start_time = time.time()
            history = await agent.run()
            elapsed = time.time() - start_time
            prov, mod = self.agent_factory.get_llm_metadata()
            metadata = WorkflowMetadata(
                creator="browser_use",
                creator_version="latest",
                browser_type="chrome",
                browser_version="unknown",
                created_at=datetime.now(UTC).isoformat(),
                original_task_prompt=task_prompt,
                execution_duration_seconds=elapsed,
                llm_provider=prov,
                llm_model_name=mod,
                os_platform="darwin",
            )
            workflow = convert_history_to_workflow(
                history, workflow_id, task_prompt, metadata
            )
            self.repository.save(workflow)
            return history.final_result() or "Workflow finished."
        finally:
            await browser.stop()


class SelfHealingRunner(WorkflowRunner[PlaywrightPage]):
    def __init__(
        self,
        replay_runner: WorkflowRunner[PlaywrightPage],
        fallback_runner: WorkflowRunner[PlaywrightPage],
        repository: WorkflowRepository,
        cdp_url: str = "http://localhost:9222",
    ) -> None:
        self.replay_runner = replay_runner
        self.fallback_runner = fallback_runner
        self.repository = repository
        self.cdp_url = cdp_url

    async def run(
        self,
        task_prompt: str,
        context: ExecutionContext[PlaywrightPage] = DEFAULT_CONTEXT,
    ) -> str:
        if context.cache_key and self.repository.exists(context.cache_key):
            try:
                return await self.replay_runner.run(task_prompt, context=context)
            except Exception as e:
                logger.warning(f"Replay failed ({e}). Falling back to LLM...")
                if context.page is not None:
                    await context.page.goto("about:blank")
                else:
                    async with httpx.AsyncClient() as client:
                        await client.get(
                            f"{self.cdp_url}/json/new?about:blank", timeout=2.0
                        )
        return await self.fallback_runner.run(task_prompt, context=context)
