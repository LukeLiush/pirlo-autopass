from pathlib import Path

from pirlo.core.models.link import LlmLink
from pirlo_autopass.adapters.browser_agent import DefaultBrowserAgentFactory

sample_link = LlmLink(
    name="test", provider="google", model="gemini-2.5-flash", api_key="dummy"
)


def test_default_browser_agent_factory_gif_defaults():
    factory = DefaultBrowserAgentFactory(link=sample_link)
    assert factory.generate_gif is False
    assert factory.get_llm_metadata() == ("google", "gemini-2.5-flash")


def test_default_browser_agent_factory_gif_boolean():
    factory = DefaultBrowserAgentFactory(link=sample_link, generate_gif=True)
    assert factory.generate_gif is True


def test_default_browser_agent_factory_generate_gif_str_path():
    gif_file = "/tmp/pirlo_runs/run_123/agent_history.gif"

    factory = DefaultBrowserAgentFactory(
        link=sample_link,
        generate_gif=gif_file,
    )
    assert factory.generate_gif == gif_file


def test_default_browser_agent_factory_generate_gif_as_path_object():
    gif_file = Path("/tmp/pirlo_runs/run_456/custom_history.gif")

    factory = DefaultBrowserAgentFactory(
        link=sample_link,
        generate_gif=gif_file,
    )
    assert factory.generate_gif == str(gif_file)
