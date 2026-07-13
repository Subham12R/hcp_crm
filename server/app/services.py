from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HCP, Interaction, Material


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
    existing = set(
        await session.scalars(
            select(Material.name).where(Material.name.in_(material_names))
        )
    )
    session.add_all(
        material
        for material in (
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
        )
        if material.name not in existing
    )

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
            )
        )

    await session.commit()