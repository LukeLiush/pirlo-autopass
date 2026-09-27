# tests/test_autopass_dag.py
from __future__ import annotations

import pytest

from pirlo.core.services.blueprint_extractor import BlueprintExtractor
from pirlo.playbooks.autopass.main import AutopassPlay
from pirlo.playbooks.autopass.models import (
    AutopassRunOutput,
)


def test_autopass_blueprint_extraction():
    """Verify the declarative DAG structure extracted via BlueprintExtractor."""
    blueprint = BlueprintExtractor.extract_from_play(AutopassPlay)
    assert len(blueprint.nodes) == 3
    node_names = [n.playbook_name for n in blueprint.nodes]
    assert node_names == ["DecomposeTaskPlay", "ExecuteSubtaskPlay", "AutopassPlay"]

    # ExecuteSubtaskPlay is mapped over DecomposeTaskPlay's task_prompts
    exec_node = blueprint.nodes[1]
    assert exec_node.is_mapped is True
    assert "subtask_prompt" in exec_node.mapped_bindings
    assert exec_node.mapped_bindings["subtask_prompt"].source_field == "task_prompts"

    # AutopassPlay fans in subtask_results
    autopass_node = blueprint.nodes[2]
    assert "subtask_results" in autopass_node.param_bindings


@pytest.mark.anyio
async def test_autopass_dag_execution(monkeypatch, tmp_path):
    monkeypatch.setenv("PIRLO_WORKSPACE", str(tmp_path))
    from pirlo.infrastructure.services.profile_manager import ProfileManager
    from pirlo.playbooks.autopass.models import SubtaskExecutionOutput

    ProfileManager.save_profile_metadata("default")

    subtask_results = [
        SubtaskExecutionOutput(
            subtask_prompt="Step 1: Open store",
            result_message="Step completed",
            success=True,
        ),
        SubtaskExecutionOutput(
            subtask_prompt="Step 2: Add keyboard to cart",
            result_message="Step completed",
            success=True,
        ),
    ]

    session = AutopassPlay()
    output: AutopassRunOutput = await session.execute(
        task="Buy keyboard",
        profile="default",
        subtask_results=subtask_results,
    )

    assert isinstance(output, AutopassRunOutput)
    assert output.task_prompt == "Buy keyboard"
    assert len(output.subtask_results) == 2
    assert output.subtask_results[0].subtask_prompt == "Step 1: Open store"
    assert output.subtask_results[1].subtask_prompt == "Step 2: Add keyboard to cart"
