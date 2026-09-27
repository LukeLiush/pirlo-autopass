from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from pirlo.core.models.actions import (
    Action,
    ActionStatus,
    ClickAction,
    DoneAction,
    ExtractContentAction,
    InputTextAction,
    NavigateAction,
    ScrollAction,
    SendKeysAction,
)
from pirlo.core.models.specifications import SafetyCandidate
from pirlo.core.models.workflow import Workflow
from playwright.async_api import Page

from .support import PageContentSanitizer, ResilientLocatorResolver, ResilientPageWaiter

logger = logging.getLogger("pirlo_autopass.playwright_adapter")


class PlaywrightAdapter:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.locator_resolver = ResilientLocatorResolver(page)
        self.page_waiter = ResilientPageWaiter(page)
        self.content_sanitizer = PageContentSanitizer()
        self.last_extraction_result: str | None = None

    async def execute_workflow(
        self,
        workflow: Workflow,
        on_step_update: Callable[[int, Action], Coroutine[Any, Any, None]]
        | None = None,
    ) -> None:
        for idx, action in enumerate(workflow.actions):
            action.step_number = idx + 1
            action.status = ActionStatus.NOT_STARTED
            action.started_at = None
            action.finished_at = None
            if on_step_update:
                await on_step_update(action.step_number, action)

        for step_idx, action in enumerate(workflow.actions):
            step_num = step_idx + 1
            action.status = ActionStatus.RUNNING
            action.started_at = datetime.now(UTC)
            if on_step_update:
                await on_step_update(step_num, action)

            try:
                candidate = await self._to_safety_candidate(action)
                action.check_safety_rules(candidate)
                await self.execute_action(action)
                action.status = ActionStatus.COMPLETED
                action.finished_at = datetime.now(UTC)
                if on_step_update:
                    await on_step_update(step_num, action)
            except Exception:
                action.status = ActionStatus.FAILED
                action.finished_at = datetime.now(UTC)
                if on_step_update:
                    await on_step_update(step_num, action)
                raise

            await asyncio.sleep(0.5)

    async def _to_safety_candidate(self, action: Action) -> SafetyCandidate:
        live_element_info = None
        if hasattr(action, "element_context") and action.element_context:
            try:
                loc = self.page.locator(f"xpath={action.element_context.xpath}").first
                tag_name = await loc.evaluate("el => el.tagName")
                text = await loc.inner_text()
                live_element_info = {"tag_name": tag_name, "text": text}
            except Exception:
                live_element_info = None
        return SafetyCandidate(
            action=action, live_url=self.page.url, live_element_info=live_element_info
        )

    async def execute_action(self, action: Action) -> None:
        match action:
            case NavigateAction(url=url):
                try:
                    await self.page.goto(
                        url, wait_until="domcontentloaded", timeout=15000
                    )
                except Exception:
                    pass
                await self.page_waiter.wait_for_load()
            case ClickAction(element_context=ctx):
                loc = await self.locator_resolver.resolve(ctx)
                try:
                    await loc.click(timeout=3000)
                except Exception:
                    await loc.evaluate("(el) => el.click()")
                await self.page_waiter.wait_for_load()
            case InputTextAction(element_context=ctx, text=text):
                loc = await self.locator_resolver.resolve(ctx, for_input=True)
                try:
                    await loc.fill("")
                    await loc.type(text)
                except Exception:
                    await self.page.keyboard.type(text)
                await self.page_waiter.wait_for_load()
            case ScrollAction(amount=amount):
                if amount is not None:
                    await self.page.evaluate(f"window.scrollBy(0, {amount});")
                else:
                    await self.page.keyboard.press("PageDown")
            case SendKeysAction(keys=keys):
                await self.page.keyboard.press(keys)
            case ExtractContentAction():
                await self.page_waiter.wait_for_text_settled()
                self.last_extraction_result = (
                    await self.content_sanitizer.extract_markdown(self.page)
                )
            case DoneAction():
                if self.last_extraction_result is not None:
                    action.text = self.last_extraction_result
                else:
                    await self.page_waiter.wait_for_text_settled()
                    action.text = await self.content_sanitizer.extract_markdown(
                        self.page
                    )
            case _:
                raise TypeError(f"Unrecognized action subclass: {type(action)}")
