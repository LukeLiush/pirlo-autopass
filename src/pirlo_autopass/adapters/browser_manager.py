from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from cloakbrowser import launch_persistent_context_async

from pirlo.infrastructure.services.profile_manager import ProfileManager
from pirlo_autopass.core.ports import BrowserManager as BaseBrowserManager


class CloakBrowserManager(BaseBrowserManager):
    """Unified manager for persistent browser process and Playwright page lifecycles."""

    def __init__(
        self, profile_path: Path, headless: bool = True, cdp_port: int = 9222
    ) -> None:
        self.profile_path = profile_path
        self.headless = headless
        self.cdp_port = cdp_port
        self._ctx: Any = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[CloakBrowserManager]:
        """Launches persistent CloakBrowser context using an isolated ephemeral worker profile."""
        worker_profile_path, cleanup = ProfileManager.create_ephemeral_worker_profile(
            self.profile_path.name
        )

        cdp_arg = (
            f"--remote-debugging-port={self.cdp_port}"
            if self.cdp_port > 0 and self.cdp_port != 9222
            else "--remote-debugging-port=0"
        )

        try:
            self._ctx = await launch_persistent_context_async(
                str(worker_profile_path),
                headless=self.headless,
                humanize=False,
                args=[cdp_arg],
            )
            yield self
        finally:
            if self._ctx:
                await self._ctx.close()
                self._ctx = None
            cleanup()

    @asynccontextmanager
    async def new_page(self) -> AsyncIterator[Any]:
        """Spawns an isolated Playwright Page and closes it on exit."""
        if not self._ctx:
            raise RuntimeError(
                "Browser session is not active. Call inside 'async with browser_manager.session()'."
            )
        page = await self._ctx.new_page()
        try:
            yield page
        finally:
            await page.close()
