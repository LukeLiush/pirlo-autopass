from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from browser_use.llm.base import BaseChatModel as BrowserUseChatModel

from pirlo.core.models.link import SUPPORTED_PROVIDERS, LlmLink

_ADAPTER_REGISTRY: dict[str, type[BrowserUseChatModelAdapter]] = {}


def register_browser_use_adapter(
    *providers: str,
) -> Callable[[type[BrowserUseChatModelAdapter]], type[BrowserUseChatModelAdapter]]:
    def decorator(
        cls: type[BrowserUseChatModelAdapter],
    ) -> type[BrowserUseChatModelAdapter]:
        for p in providers:
            _ADAPTER_REGISTRY[p.lower().strip()] = cls
        return cls

    return decorator


class BrowserUseChatModelAdapter(ABC):
    @abstractmethod
    def convert(self, link: LlmLink, **kwargs: Any) -> BrowserUseChatModel: ...


@register_browser_use_adapter("google", "gemini")
class GoogleChatModelAdapter(BrowserUseChatModelAdapter):
    def convert(self, link: LlmLink, **kwargs: Any) -> BrowserUseChatModel:
        from browser_use.llm.google.chat import ChatGoogle

        return ChatGoogle(
            model=link.model, api_key=link.api_key or None, **kwargs
        )


@register_browser_use_adapter("anthropic")
class AnthropicChatModelAdapter(BrowserUseChatModelAdapter):
    def convert(self, link: LlmLink, **kwargs: Any) -> BrowserUseChatModel:
        from browser_use.llm.anthropic.chat import ChatAnthropic

        return ChatAnthropic(
            model=link.model, api_key=link.api_key or None, **kwargs
        )


@register_browser_use_adapter("openai", "dashscope")
class OpenAIChatModelAdapter(BrowserUseChatModelAdapter):
    def convert(self, link: LlmLink, **kwargs: Any) -> BrowserUseChatModel:
        from browser_use.llm.openai.chat import ChatOpenAI

        base_url = link.base_url or SUPPORTED_PROVIDERS.get(
            link.provider.lower(), {}
        ).get("default_base_url")
        return ChatOpenAI(
            model=link.model,
            api_key=link.api_key or None,
            base_url=base_url or None,
            **kwargs,
        )


class BrowserUseAdapterRegistry:
    @classmethod
    def to_chat_model(cls, link: LlmLink, **kwargs: Any) -> BrowserUseChatModel:
        adapter_cls = _ADAPTER_REGISTRY.get(
            link.provider.lower().strip(), OpenAIChatModelAdapter
        )
        return adapter_cls().convert(link, **kwargs)
