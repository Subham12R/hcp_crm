from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    specialty: Mapped[str] = mapped_column(String(100))
    organization: Mapped[str] = mapped_column(String(160))
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    interactions: Mapped[list[Interaction]] = relationship(back_populates="hcp")
    follow_ups: Mapped[list[FollowUp]] = relationship(back_populates="hcp")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    product: Mapped[str] = mapped_column(String(100))
    material_type: Mapped[str] = mapped_column(String(30))
    specialties: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_approved: Mapped[bool] = mapped_column(default=True)
    topic_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    distributions: Mapped[list[InteractionMaterial]] = relationship(back_populates="material")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), index=True)
    interaction_type: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attendees: Mapped[list[str]] = mapped_column(JSONB, default=list)
    topics: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    channel: Mapped[str] = mapped_column(String(30))
    outcome: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    hcp: Mapped[HCP] = relationship(back_populates="interactions")
    distributions: Mapped[list[InteractionMaterial]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list[FollowUp]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    follow_up_actions: Mapped[str] = mapped_column(Text, default="")


class InteractionMaterial(Base):
    __tablename__ = "interaction_materials"
    __table_args__ = (
        UniqueConstraint(
            "interaction_id",
            "material_id",
            "distribution_type",
            name="uq_interaction_material_distribution",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interactions.id"))
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    distribution_type: Mapped[str] = mapped_column(String(20))  # material | sample
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    interaction: Mapped[Interaction] = relationship(back_populates="distributions")
    material: Mapped[Material] = relationship(back_populates="distributions")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), index=True)
    interaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("interactions.id"), nullable=True
    )
    due_on: Mapped[date] = mapped_column(Date)
    purpose: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")

    hcp: Mapped[HCP] = relationship(back_populates="follow_ups")
    interaction: Mapped[Interaction | None] = relationship(back_populates="follow_ups")