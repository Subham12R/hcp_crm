# HCP Interaction CRM

An AI-first CRM for life-sciences field representatives to record Healthcare Professional (HCP) interactions, retrieve HCP context, recommend approved materials, and schedule follow-ups.

## Run with Docker

Prerequisites: Docker Desktop and a Groq API key.

```powershell
Copy-Item .env.example .env
# Set GROQ_API_KEY in .env
docker compose up --build
```

Open:

- Frontend: <http://localhost:8080>
- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>

Compose starts PostgreSQL, applies Alembic migrations, seeds the demo data, then starts the API and frontend. The database is retained in the `postgres_data` Docker volume.

Stop the stack with `docker compose down`. Use `docker compose down -v` only when you want to remove the database data as well.

## Run locally

Prerequisites: Python 3.14, [uv](https://docs.astral.sh/uv/), Node.js, npm, PostgreSQL, and a Groq API key.

1. Create a PostgreSQL database named `hcp_crm` and configure `server/.env`:

   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:URL_ENCODED_PASSWORD@localhost:5432/hcp_crm
   GROQ_API_KEY=your_groq_api_key
   ```

2. Start the backend:

   ```powershell
   cd server
   uv sync
   uv run alembic upgrade head
   uv run python -m app.seed
   uv run uvicorn main:app --reload
   ```

3. In another terminal, start the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

The local frontend runs at <http://localhost:5173> and calls the API at `http://127.0.0.1:8000/api` by default. See [frontend/README.md](frontend/README.md) for frontend-specific commands and [server/README.md](server/README.md) for backend details.

## License

This repository is an assignment submission and is not free to use. See [LICENSE](LICENSE).
