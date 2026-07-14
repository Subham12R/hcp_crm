import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app import api
from app.models import HCP
from app.schemas import ChatRequest
from app.services import get_hcp_profile


class CapturingSession:
    def __init__(self) -> None:
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return HCP(
            id=1,
            name="Dr. Smith",
            specialty="Cardiology",
            organization="City Heart Institute",
            priority="high",
        )


@pytest.mark.asyncio
async def test_profile_lookup_ignores_case_and_periods() -> None:
    session = CapturingSession()

    profile = await get_hcp_profile(session, "dr smith")

    query = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert profile.name == "Dr. Smith"
    assert "lower(replace(hcps.name, '.', '')) = 'dr smith'" in query


@pytest.mark.asyncio
async def test_chat_returns_not_found_for_an_unknown_hcp(monkeypatch) -> None:
    async def missing_hcp(*_args, **_kwargs):
        raise ValueError("HCP 'Unknown' was not found")

    monkeypatch.setattr(api, "run_agent", missing_hcp)

    with pytest.raises(HTTPException) as error:
        await api.chat(ChatRequest(message="Show Unknown"), object())

    assert error.value.status_code == 404
