from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any


class BrowserManager(ABC):
    """Port for browser process session and page lifecycle operations."""

    @abstractmethod
    def session(self) -> AbstractAsyncContextManager[Any]:
        """Launches browser session on enter, closes on exit."""

    @abstractmethod
    def new_page(self) -> AbstractAsyncContextManager[Any]:
        """Spawns an isolated page on enter, closes on exit."""
