# src/pirlo/playbooks/autopass/main.py
from __future__ import annotations

from typing import Annotated

from pirlo.core.decorators import play
from pirlo.core.instructions import AutopassInstructions
from pirlo.core.models.link import LlmLink
from pirlo.core.models.parameters import LinkParameter, Parameter
from pirlo.core.ports.play import Play, requires
from pirlo.infrastructure.services.profile_manager import ProfileManager
from pirlo_autopass.models import (
    AutopassRunOutput,
    SubtaskExecutionOutput,
)
from pirlo_autopass.subplays import (
    ExecuteSubtaskPlay,
    QuickProgressListener,
)

__all__ = ["AutopassPlay", "QuickProgressListener"]


@play(
    name="autopass",
    description="Run self-healing decomposed browser automation workflows.",
)
class AutopassPlay(Play[AutopassRunOutput]):
    """Top-level Autopass orchestration Play aggregating decomposed subtask executions."""

    subtask_results: list[SubtaskExecutionOutput] = requires(ExecuteSubtaskPlay)

    async def execute(
        self,
        task: Annotated[
            str, Parameter(help="Task prompt to execute autonomously")
        ] = "",
        profile: Annotated[str, Parameter(help="Browser profile name")] = "default",
        headless: Annotated[
            bool, Parameter(help="Run browser in headless mode")
        ] = False,
        playmaker: Annotated[
            LlmLink | None, LinkParameter(help="Playmaker LLM link")
        ] = None,
        use_vision: Annotated[
            bool, Parameter(help="Enable vision for the Agent")
        ] = False,
        max_failures: Annotated[
            int, Parameter(help="Max consecutive step failures allowed")
        ] = 3,
        retry_delay: Annotated[
            int, Parameter(help="Delay in seconds between retries")
        ] = 5,
        subtask_results: Annotated[
            list[SubtaskExecutionOutput] | None,
            Parameter(help="Subtask execution outputs"),
        ] = None,
        *args: object,
        **kwargs: object,
    ) -> AutopassRunOutput:
        if not ProfileManager.exists(profile):
            instruction = AutopassInstructions.PROFILE_MISSING.format(
                profile=profile, existing_info=""
            )
            self.ui.yellow_card(instruction)
            raise ValueError(str(instruction))

        if not task:
            self.ui.yellow_card(AutopassInstructions.TASK_REQUIRED)
            raise ValueError(str(AutopassInstructions.TASK_REQUIRED))

        self.ui.header("Autopass Execution", subtitle=f"Task: {task}")

        raw_list = subtask_results or getattr(self, "subtask_results", [])
        results_list: list[SubtaskExecutionOutput] = []
        for item in raw_list:
            if isinstance(item, list):
                results_list.extend(item)
            elif isinstance(item, SubtaskExecutionOutput):
                results_list.append(item)

        successful_count = sum(1 for s in results_list if s.success)
        total_count = len(results_list)

        details = "\n".join(
            f"  • Subtask '{s.subtask_prompt}': {s.result_message}"
            for s in results_list
        )
        final_msg = (
            f"Task '{task}' completed ({successful_count}/{total_count} subtasks successful):\n{details}"
            if results_list
            else f"Task '{task}' completed with no subtasks executed."
        )

        self.ui.goal(
            message=f"Autopass finished: {successful_count}/{total_count} subtasks successful",
            detail=final_msg,
        )

        return AutopassRunOutput(
            task_prompt=task,
            final_message=final_msg,
            subtask_results=results_list,
            actions_count=total_count,
        )


if __name__ == "__main__":
    AutopassPlay.cli()
