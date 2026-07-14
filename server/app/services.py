from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HCP, Interaction, InteractionMaterial, Material
from app.schemas import InteractionCreate
from sqlalchemy.orm import selectinload
from app.models import FollowUp

from app.schemas import (
    FollowUpCreate,
    FollowUpRead,
    HCPProfile,
    InteractionHistoryItem,
    MaterialRead,
)

async def seed_demo_data(session: AsyncSession) -> None:
    hcp = await session.scalar(select(HCP).where(HCP.name == "Dr. Smith"))
    if hcp is None:
        hcp = HCP(
            name="Dr. Smith",
            specialty="Cardiology",
            organization="City Heart Institute",
            priority="high",
        )
        session.add(hcp)
        await session.flush()

    material_names = {
        "Product X Efficacy Brochure",
        "Product X Dosing Guide",
    }
    existing_material_names = set(
        (await session.scalars(select(Material.name).where(Material.name.in_(material_names)))).all()
    )

    new_materials = [
        Material(
            name="Product X Efficacy Brochure",
            product="Product X",
            material_type="brochure",
            specialties=["Cardiology"],
            is_approved=True,
        ),
        Material(
            name="Product X Dosing Guide",
            product="Product X",
            material_type="guide",
            specialties=["Cardiology"],
            is_approved=True,
        ),
    ]
    session.add_all(
        material for material in new_materials if material.name not in existing_material_names
    )

    topic_tags = {
        "Product X Efficacy Brochure": ["efficacy", "safety", "patient outcomes"],
        "Product X Dosing Guide": ["dosing", "administration"],
    }
    
    for material in (
        await session.scalars(
            select(Material).where(Material.name.in_(material_names))
        )
    ).all():
        material.topic_tags = topic_tags[material.name]

    prior_interaction = await session.scalar(
        select(Interaction).where(Interaction.hcp_id == hcp.id)
    )
    if prior_interaction is None:
        session.add(
            Interaction(
                hcp_id=hcp.id,
                interaction_type="meeting",
                occurred_at=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
                channel="face-to-face",
                topics="Product X safety profile",
                notes="Requested efficacy evidence for the next meeting.",
                outcome="Interested in follow-up",
                sentiment="neutral",
                follow_up_actions="Share efficacy brochure at the next meeting.",
            )
        )

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def normalized_hcp_name(hcp_name: str) -> str:
    return hcp_name.lower().replace(".", "").strip()


def hcp_name_filter(hcp_name: str):
    return func.lower(func.replace(HCP.name, ".", "")) == normalized_hcp_name(hcp_name)
async def get_hcp_by_name(session: AsyncSession, hcp_name: str) -> HCP | None:
    return await session.scalar(select(HCP).where(hcp_name_filter(hcp_name)))

async def get_hcp_profile(
    session: AsyncSession,
    hcp_name: str,
) -> HCPProfile:
    hcp = await session.scalar(
        select(HCP)
        .options(selectinload(HCP.interactions))
        .where(hcp_name_filter(hcp_name))
    )
    if hcp is None:
        raise ValueError(f"HCP '{hcp_name}' was not found")

    history = sorted(
        hcp.interactions,
        key=lambda interaction: interaction.occurred_at,
        reverse=True,
    )

    return HCPProfile(
        id=hcp.id,
        name=hcp.name,
        specialty=hcp.specialty,
        organization=hcp.organization,
        priority=hcp.priority,
        interaction_history=[
            InteractionHistoryItem(
                id=interaction.id,
                occurred_at=interaction.occurred_at,
                interaction_type=interaction.interaction_type,
                topics=interaction.topics,
                outcome=interaction.outcome,
                sentiment=interaction.sentiment,
            )
            for interaction in history
        ],
    )


async def recommend_materials(
    session: AsyncSession,
    hcp_name: str,
    discussion_topic: str,
) -> list[MaterialRead]:
    hcp = await get_hcp_by_name(session, hcp_name)
    if hcp is None:
        raise ValueError(f"HCP '{hcp_name}' was not found")

    topic_terms = {
        term.strip(".,!?").lower()
        for term in discussion_topic.split()
        if len(term.strip(".,!?")) > 2
    }
    materials = (
        await session.scalars(
            select(Material).where(
                Material.is_approved.is_(True),
                Material.specialties.contains([hcp.specialty]),
            )
        )
    ).all()

    return [
        MaterialRead(
            id=material.id,
            name=material.name,
            product=material.product,
            material_type=material.material_type,
            topic_tags=material.topic_tags,
        )
        for material in materials
        if topic_terms.intersection(material.topic_tags)
    ]


async def create_follow_up(
    session: AsyncSession,
    payload: FollowUpCreate,
) -> FollowUpRead:
    hcp = await get_hcp_by_name(session, payload.hcp_name)
    if hcp is None:
        raise ValueError(f"HCP '{payload.hcp_name}' was not found")

    hcp_name = hcp.name

    follow_up = FollowUp(
        hcp_id=hcp.id,
        due_on=payload.due_on,
        purpose=payload.purpose,
        next_action=payload.next_action,
    )
    session.add(follow_up)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(follow_up)
    return FollowUpRead(
        id=follow_up.id,
        hcp_name=hcp_name,
        due_on=follow_up.due_on,
        purpose=follow_up.purpose,
        next_action=follow_up.next_action,
        status=follow_up.status,
    )
    
async def create_interaction(
    session: AsyncSession,
    payload: InteractionCreate,
) -> Interaction:
    hcp = await get_hcp_by_name(session, payload.hcp_name)
    if hcp is None:
        raise ValueError(f"HCP '{payload.hcp_name}' was not found")

    distributions: list[InteractionMaterial] = []
    seen_distributions: set[tuple[str, str]] = set()

    for item in payload.distributions:
        key = (item.material_name, item.distribution_type)
        if key in seen_distributions:
            raise ValueError(f"Duplicate {item.distribution_type}: {item.material_name}")
        seen_distributions.add(key)

        material = await session.scalar(
            select(Material).where(
                Material.name == item.material_name,
                Material.is_approved.is_(True),
            )
        )
        if material is None:
            raise ValueError(f"Approved material '{item.material_name}' was not found")

        distributions.append(
            InteractionMaterial(
                material_id=material.id,
                distribution_type=item.distribution_type,
                quantity=item.quantity,
            )
        )

    interaction = Interaction(
        hcp_id=hcp.id,
        interaction_type=payload.interaction_type,
        occurred_at=payload.occurred_at,
        attendees=payload.attendees,
        topics=payload.topics or "",
        notes=payload.notes or "",
        channel=payload.channel,
        outcome=payload.outcome or "",
        sentiment=payload.sentiment,
        follow_up_actions=payload.follow_up_actions or "",
        distributions=distributions,
    )

    session.add(interaction)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(interaction)
    return interaction