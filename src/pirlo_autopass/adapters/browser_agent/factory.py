from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from browser_use import Agent, Browser, Controller

from pirlo.core.models.link import LlmLink

from .adapters import BrowserUseAdapterRegistry


class BrowserAgentFactory(ABC):
    @abstractmethod
    def create_agent(
        self,
        task: str,
        browser: Browser | None = None,
        browser_context: Any | None = None,
    ) -> Agent: ...

    @abstractmethod
    def get_llm_metadata(self) -> tuple[str, str]: ...


class DefaultBrowserAgentFactory(BrowserAgentFactory):
    def __init__(
        self,
        link: LlmLink,
        controller: Controller | None = None,
        use_vision: bool = False,
        generate_gif: bool | str | Path = False,
    ):
        self.link = link
        self.controller = controller or Controller()
        self.use_vision = use_vision
        self.generate_gif = (
            str(generate_gif) if isinstance(generate_gif, Path) else generate_gif
        )

    def create_agent(
        self,
        task: str,
        browser: Browser | None = None,
        browser_context: Any | None = None,
    ) -> Agent:
        llm = BrowserUseAdapterRegistry.to_chat_model(self.link)
        kwargs: dict[str, Any] = {
            "task": task,
            "llm": llm,
            "keep_alive": True,
            "controller": self.controller,
            "use_vision": self.use_vision,
            "generate_gif": self.generate_gif,
        }
        if browser is not None:
            kwargs["browser"] = browser
        if browser_context is not None:
            kwargs["browser_context"] = browser_context
        return Agent(**kwargs)

    def get_llm_metadata(self) -> tuple[str, str]:
        return self.link.provider, self.link.model
