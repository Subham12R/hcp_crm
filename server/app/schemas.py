from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MaterialDistributionInput(BaseModel):
    material_name: str = Field(min_length=1, max_length=160)
    distribution_type: Literal["material", "sample"]
    quantity: int = Field(default=1, ge=1)


class InteractionDraft(BaseModel):
    hcp_name: str | None = None
    interaction_type: str | None = None
    occurred_at: datetime | None = None
    attendees: list[str] = Field(default_factory=list)
    topics: str | None = None
    notes: str | None = None
    distributions: list[MaterialDistributionInput] = Field(default_factory=list)
    channel: str | None = None
    outcome: str | None = None
    sentiment: Literal["positive", "neutral", "negative"] | None = None
    follow_up_actions: str | None = None


class InteractionCreate(BaseModel):
    hcp_name: str = Field(min_length=1, max_length=160)
    interaction_type: str = Field(min_length=1, max_length=30)
    occurred_at: datetime
    attendees: list[str] = Field(default_factory=list)
    topics: str | None = None
    notes: str | None = None
    distributions: list[MaterialDistributionInput] = Field(default_factory=list)
    channel: str = Field(min_length=1, max_length=30)
    outcome: str | None = None
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    follow_up_actions: str | None = None

class InteractionRead(InteractionCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteractionSaved(BaseModel):
    id: int
    hcp_name: str
    occurred_at: datetime
    outcome: str
    created_at: datetime

class InteractionHistoryItem(BaseModel):
    id: int
    occurred_at: datetime
    interaction_type: str
    topics: str
    outcome: str
    sentiment: str


class HCPProfile(BaseModel):
    id: int
    name: str
    specialty: str
    organization: str
    priority: str
    interaction_history: list[InteractionHistoryItem] = Field(default_factory=list)


class FollowUpRead(BaseModel):
    id: int
    hcp_name: str
    due_on: date
    purpose: str
    next_action: str
    status: str

class MaterialRead(BaseModel):
    id: int
    name: str
    product: str
    material_type: str
    topic_tags: list[str]

class FollowUpCreate(BaseModel):
    hcp_name: str = Field(min_length=1, max_length=160)
    due_on: date
    purpose: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    draft: InteractionDraft = Field(default_factory=InteractionDraft)


class ToolActivity(BaseModel):
    tool_name: str
    summary: str


class ChatResponse(BaseModel):
    message: str
    draft_patch: InteractionDraft = Field(default_factory=InteractionDraft)
    tool_activity: list[ToolActivity] = Field(default_factory=list)