import hashlib
import re
from typing import Any

from pirlo.core.models.execution_context import ExecutionContext
from pirlo.core.services import WorkflowRunner
from pirlo_autopass.core.ports import (
    BrowserManager,
    ProgressListener,
)


def slugify(text: str) -> str:
    """Converts a task prompt into a safe, normalized, unique string identifier for cache keys."""
    raw = text.lower().strip()
    clean = re.sub(r"[^\w\s-]", "", raw)
    normalized = re.sub(r"[\s_-]+", "_", clean)[:35]
    prompt_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return f"{normalized}_{prompt_hash}" if normalized else prompt_hash


class RunAutopassUseCase:
    """Application Service (Use Case) coordinating workflow execution on active browser pages."""

    def __init__(
        self,
        workflow_runner: WorkflowRunner,
        browser_manager: BrowserManager | None = None,
    ):
        self.workflow_runner = workflow_runner
        self._browser_manager = browser_manager

    async def run(
        self,
        task_prompt: str,
        listener: ProgressListener,
        browser_manager: BrowserManager | None = None,
        run_name: str | None = None,
        run_id: str | None = None,
    ) -> Any:
        mgr = browser_manager or self._browser_manager
        if not mgr:
            raise ValueError("A BrowserManager instance is required.")

        async with mgr.new_page() as page:
            slug_prompt = slugify(task_prompt)
            cache_key = f"{run_name}_{slug_prompt}" if run_name else slug_prompt
            context = ExecutionContext(
                page=page,
                cache_key=cache_key,
                run_id=run_id,
            )

            try:
                with listener.status_context("Executing autonomous autopass play..."):
                    result = await self.workflow_runner.run(
                        task_prompt=task_prompt,
                        context=context,
                    )

                listener.show_goal(
                    "Play completed successfully!", detail=f"Result: {result}"
                )
                return result
            except Exception as e:
                listener.show_red_card("Play failed with error!", detail=str(e))
                raise
