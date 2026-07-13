from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.graph import run_agent
from app.database import get_db
from app.schemas import (
    FollowUpCreate,
    FollowUpRead,
    HCPProfile,
    InteractionCreate,
    InteractionSaved,
    MaterialRead,
    ChatRequest,
    ChatResponse,
)
from app.services import (
    create_follow_up,
    create_interaction,
    get_hcp_profile,
    recommend_materials,
)

router = APIRouter(tags=["interactions"])

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    return await run_agent(request, session)
    
@router.post(
    "/interactions",
    response_model=InteractionSaved,
    status_code=status.HTTP_201_CREATED,
)
async def save_interaction(
    payload: InteractionCreate,
    session: AsyncSession = Depends(get_db),
) -> InteractionSaved:
    try:
        interaction = await create_interaction(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return InteractionSaved(
        id=interaction.id,
        hcp_name=payload.hcp_name,
        occurred_at=interaction.occurred_at,
        outcome=interaction.outcome,
        created_at=interaction.created_at,
    )

@router.get("/hcps/{hcp_name}", response_model=HCPProfile)
async def hcp_profile(
    hcp_name: str,
    session: AsyncSession = Depends(get_db),
) -> HCPProfile:
    try:
        return await get_hcp_profile(session, hcp_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/materials", response_model=list[MaterialRead])
async def material_recommendations(
    hcp_name: str = Query(min_length=1),
    topic: str = Query(min_length=1),
    session: AsyncSession = Depends(get_db),
) -> list[MaterialRead]:
    try:
        return await recommend_materials(session, hcp_name, topic)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/follow-ups",
    response_model=FollowUpRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_follow_up(
    payload: FollowUpCreate,
    session: AsyncSession = Depends(get_db),
) -> FollowUpRead:
    try:
        return await create_follow_up(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc