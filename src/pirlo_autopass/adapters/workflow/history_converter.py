from __future__ import annotations

from browser_use.agent.views import AgentHistoryList

from pirlo.core.models.actions import (
    Action,
    ClickAction,
    DoneAction,
    ElementContext,
    ExtractContentAction,
    InputTextAction,
    NavigateAction,
    ScrollAction,
    SendKeysAction,
)
from pirlo.core.models.workflow import Workflow, WorkflowMetadata


def convert_history_to_workflow(
    history_list: AgentHistoryList,
    workflow_id: str,
    description: str,
    metadata: WorkflowMetadata,
) -> Workflow:
    actions: list[Action] = []
    for item in history_list.history:
        if not item.model_output or not item.model_output.action:
            continue
        for sub_act in item.model_output.action:
            act_dict = sub_act.model_dump(exclude_none=True)
            for act_name, act_params in act_dict.items():
                match act_name:
                    case "go_to_url":
                        actions.append(NavigateAction(url=act_params["url"]))
                    case "click_element_node":
                        actions.append(
                            ClickAction(
                                element_context=ElementContext(
                                    xpath=act_params.get("xpath", "")
                                )
                            )
                        )
                    case "input_text":
                        actions.append(
                            InputTextAction(
                                text=act_params["text"],
                                element_context=ElementContext(
                                    xpath=act_params.get("xpath", "")
                                ),
                            )
                        )
                    case "scroll":
                        actions.append(
                            ScrollAction(amount=act_params.get("amount", 500))
                        )
                    case "send_keys":
                        actions.append(SendKeysAction(keys=act_params["keys"]))
                    case "extract_page_content":
                        actions.append(ExtractContentAction())
                    case "done":
                        actions.append(
                            DoneAction(text=act_params.get("text", "Done"))
                        )
    return Workflow(
        workflow_id=workflow_id,
        description=description,
        actions=actions,
        metadata=metadata,
    )
