# src/pirlo/playbooks/autopass/models.py
from __future__ import annotations

from dataclasses import field

from pirlo.core.models.blueprint import PlayOutput


class TaskDecompositionOutput(PlayOutput):
    """Output payload from task decomposition."""

    task_prompts: list[str] = field(default_factory=list)
    total_subtasks: int = 0


class SubtaskExecutionOutput(PlayOutput):
    """Output payload from running ONE single subtask prompt."""

    subtask_prompt: str
    result_message: str
    success: bool = True


class AutopassRunOutput(PlayOutput):
    """Final merged output payload returned by the Autopass DAG."""

    task_prompt: str | None
    final_message: str
    subtask_results: list[SubtaskExecutionOutput] = field(default_factory=list)
    actions_count: int = 0
    output_files: list[str] = field(default_factory=list)
