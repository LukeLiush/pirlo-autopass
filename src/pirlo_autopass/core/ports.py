from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any


class BrowserManager(ABC):
    """Port for browser process session and page lifecycle operations."""

    @abstractmethod
    def session(self) -> AbstractAsyncContextManager[Any]:
        """Launches browser session on enter, closes on exit."""

    @abstractmethod
    def new_page(self) -> AbstractAsyncContextManager[Any]:
        """Spawns an isolated page on enter, closes on exit."""


class ProgressListener(ABC):
    """Port for presenting status updates and notifications to the user."""

    @abstractmethod
    def status_context(self, message: str) -> AbstractContextManager[Any]:
        """A context manager displaying a pending/loading status message."""

    @abstractmethod
    def show_warning(self, message: Any, detail: str | None = None) -> None:
        """Display a warning to the user."""

    @abstractmethod
    def show_goal(self, message: str, detail: str | None = None) -> None:
        """Display a success/completion message."""

    @abstractmethod
    def show_red_card(self, message: str, detail: str | None = None) -> None:
        """Display an error/failure message."""
