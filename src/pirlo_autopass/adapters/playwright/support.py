from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from playwright.async_api import Locator, Page

from pirlo.core.models.actions import ElementContext

logger = logging.getLogger(__name__)


class PageContentSanitizer:
    def __init__(self) -> None:
        try:
            import html2text

            self._converter = html2text.HTML2Text()
            self._converter.ignore_links = False
            self._converter.ignore_images = True
            self._converter.body_width = 0
        except ImportError:
            self._converter = None

    async def extract_markdown(self, page: Page) -> str:
        html = await page.content()
        if self._converter is not None:
            return self._converter.handle(html).strip()
        # Fallback if html2text is not installed
        clean = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", clean).strip()


class ResilientPageWaiter:
    def __init__(self, page: Page) -> None:
        self.page = page

    async def wait_for_load(self) -> None:
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    async def wait_for_text_settled(
        self, check_interval: float = 0.5, max_checks: int = 4
    ) -> None:
        prev_len = -1
        for _ in range(max_checks):
            await asyncio.sleep(check_interval)
            try:
                cur_len = len(await self.page.inner_text("body"))
            except Exception:
                break
            if cur_len == prev_len:
                break
            prev_len = cur_len


class ResilientLocatorResolver:
    def __init__(self, page: Page, timeout_ms: int = 3000) -> None:
        self.page = page
        self.timeout_ms = timeout_ms

    async def resolve(self, ctx: ElementContext, for_input: bool = False) -> Locator:
        if ctx.xpath:
            loc = self.page.locator(f"xpath={ctx.xpath}").first
            try:
                await loc.wait_for(state="attached", timeout=self.timeout_ms)
                return loc
            except Exception:
                logger.debug(f"XPath fallback triggered for {ctx.xpath}")
        if ctx.text:
            loc = self.page.get_by_text(ctx.text, exact=False).first
            try:
                await loc.wait_for(state="attached", timeout=self.timeout_ms)
                return loc
            except Exception:
                pass
        raise RuntimeError(f"Unable to resolve locator for element context: {ctx}")
