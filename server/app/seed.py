import asyncio

from app.database import SessionLocal
from app.services import seed_demo_data


async def main() -> None:
    async with SessionLocal() as session:
        await seed_demo_data(session)


if __name__ == "__main__":
    asyncio.run(main())