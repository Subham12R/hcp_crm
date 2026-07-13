import json
import operator
from datetime import date
from typing import Annotated, Any

from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.tools import ToolRuntime, tool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

from app.config import get_settings
from app.schemas import (
    ChatRequest,
    ChatResponse,
    FollowUpCreate,
    InteractionCreate,
    InteractionDraft,
    ToolActivity,
)
from app.services import (
    create_follow_up as save_follow_up,
    create_interaction as save_interaction,
    get_hcp_profile as fetch_hcp_profile,
    recommend_materials as find_recommended_materials,
)


class AgentContext(TypedDict):
    session: AsyncSession


class AgentState(MessagesState):
    draft: dict[str, Any]
    tool_activity: Annotated[list[dict[str, str]], operator.add]


def tool_result(
    runtime: ToolRuntime[AgentContext],
    tool_name: str,
    summary: str,
    payload: dict[str, Any],
    draft: dict[str, Any] | None = None,
) -> Command:
    update: dict[str, Any] = {
        "messages": [
            ToolMessage(
                content=json.dumps(payload, default=str),
                tool_call_id=runtime.tool_call_id,
            )
        ],
        "tool_activity": [
            {
                "tool_name": tool_name,
                "summary": summary,
            }
        ],
    }

    if draft is not None:
        update["draft"] = draft

    return Command(update=update)

# 
@tool
def edit_interaction(
    details: InteractionDraft,
    runtime: ToolRuntime[AgentContext],
) -> Command:
    """Apply extracted or user-requested interaction fields from the details object."""
    patch = details.model_dump(
        exclude_none=True,
        exclude_unset=True,
        mode="json",
    )
    updated_draft = {**runtime.state["draft"], **patch}

    return tool_result(
        runtime=runtime,
        tool_name="edit_interaction",
        summary=f"Updated {', '.join(patch) or 'no'} fields",
        payload={"draft_patch": patch},
        draft=updated_draft,
    )

@tool
async def get_hcp_profile(
    hcp_name: str,
    runtime: ToolRuntime[AgentContext],
) -> Command:
    """Fetch an HCP's specialty, organization, priority, and interaction history."""
    if runtime.context is None:
        raise RuntimeError("Agent database session is missing")

    profile = await fetch_hcp_profile(runtime.context["session"], hcp_name)

    return tool_result(
        runtime=runtime,
        tool_name="get_hcp_profile",
        summary=f"Loaded profile for {profile.name}",
        payload=profile.model_dump(mode="json"),
    )


@tool
async def recommend_materials(
    hcp_name: str,
    topic: str,
    runtime: ToolRuntime[AgentContext],
) -> Command:
    """Recommend approved materials for an HCP's specialty and discussion topic."""
    if runtime.context is None:
        raise RuntimeError("Agent database session is missing")

    materials = await find_recommended_materials(
        runtime.context["session"],
        hcp_name,
        topic,
    )

    return tool_result(
        runtime=runtime,
        tool_name="recommend_materials",
        summary=f"Found {len(materials)} approved material recommendation(s)",
        payload={"materials": [material.model_dump(mode="json") for material in materials]},
    )


@tool
async def create_follow_up(
    hcp_name: str,
    due_on: date,
    purpose: str,
    next_action: str,
    runtime: ToolRuntime[AgentContext],
) -> Command:
    """Create a dated HCP follow-up task. Use an ISO date: YYYY-MM-DD."""
    if runtime.context is None:
        raise RuntimeError("Agent database session is missing")

    follow_up = await save_follow_up(
        runtime.context["session"],
        FollowUpCreate(
            hcp_name=hcp_name,
            due_on=due_on,
            purpose=purpose,
            next_action=next_action,
        ),
    )
    updated_draft = {
        **runtime.state["draft"],
        "follow_up_actions": next_action,
    }

    return tool_result(
        runtime=runtime,
        tool_name="create_follow_up",
        summary=f"Created follow-up for {follow_up.due_on.isoformat()}",
        payload=follow_up.model_dump(mode="json"),
        draft=updated_draft,
    )


@tool
async def log_interaction(
    runtime: ToolRuntime[AgentContext],
) -> Command:
    """Validate and save the current completed interaction draft to PostgreSQL."""
    if runtime.context is None:
        raise RuntimeError("Agent database session is missing")

    payload = InteractionCreate.model_validate(runtime.state["draft"])
    interaction = await save_interaction(runtime.context["session"], payload)

    return tool_result(
        runtime=runtime,
        tool_name="log_interaction",
        summary=f"Saved interaction #{interaction.id}",
        payload={
            "id": interaction.id,
            "hcp_name": payload.hcp_name,
            "occurred_at": interaction.occurred_at.isoformat(),
            "outcome": interaction.outcome,
        },
    )


TOOLS = [
    edit_interaction,
    get_hcp_profile,
    recommend_materials,
    create_follow_up,
    log_interaction,
]

def build_graph():
    system_prompt = f"""
You are the HCP CRM assistant. Today is {date.today().isoformat()}.

Use exactly one tool per user message.

- For a meeting description, use edit_interaction.
- For an HCP lookup, use get_hcp_profile.
- For approved material suggestions, use recommend_materials.
- For an explicit dated follow-up request, use create_follow_up.
- Only use log_interaction when the user explicitly asks to save or log.

Never invent clinical or meeting details.
"""

    base_model = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=get_settings().groq_api_key,
    )
    tool_model = base_model.bind_tools(TOOLS)

    async def assistant_node(state: AgentState) -> dict[str, list]:
        response = await tool_model.ainvoke(
            [SystemMessage(content=system_prompt), *state["messages"]]
        )
        return {"messages": [response]}

    async def respond_node(state: AgentState) -> dict[str, list]:
        response = await base_model.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Give a concise confirmation based only on the completed "
                        "tool result. Do not call tools or claim unfinished actions."
                    )
                ),
                *state["messages"],
            ]
        )
        return {"messages": [response]}

    workflow = StateGraph(AgentState, context_schema=AgentContext)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", ToolNode(TOOLS))
    workflow.add_node("respond", respond_node)

    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges(
        "assistant",
        tools_condition,
        {"tools": "tools", END: END},
    )
    workflow.add_edge("tools", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()

    
async def run_agent(
    request: ChatRequest,
    session: AsyncSession,
) -> ChatResponse:
    graph = build_graph()
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "draft": request.draft.model_dump(
                exclude_none=True,
                mode="json",
            ),
            "tool_activity": [],
        },
        context={"session": session},
        config={"recursion_limit": 8},
    )

    final_content = result["messages"][-1].content
    message = (
        final_content
        if isinstance(final_content, str)
        else json.dumps(final_content)
    )

    return ChatResponse(
        message=message,
        draft_patch=InteractionDraft.model_validate(result["draft"]),
        tool_activity=[
            ToolActivity.model_validate(activity)
            for activity in result["tool_activity"]
        ],
    )