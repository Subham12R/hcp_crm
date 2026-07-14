# HCP Interaction CRM — Backend

FastAPI backend for an AI-first CRM workflow used by life-sciences field representatives to log Healthcare Professional (HCP) interactions.

The AI assistant uses **Groq** through LangChain and a **LangGraph** workflow to extract meeting details into a structured draft, look up HCP context, recommend approved material, create follow-ups, and save a completed interaction to PostgreSQL.

## Stack

| Area | Technology |
| --- | --- |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy async ORM + asyncpg |
| Schema migrations | Alembic |
| LLM provider | Groq (`llama-3.3-70b-versatile`) |
| Agent orchestration | LangGraph |
| LLM and tool integration | LangChain |

## Architecture

```mermaid
flowchart LR
    UI["React + Redux client"] -->|"message + current draft"| API["FastAPI /api/chat"]
    API --> AGENT["LangGraph run_agent"]
    AGENT --> MODEL["LangChain ChatGroq"]
    MODEL -->|"tool call"| TOOLS["LangGraph ToolNode"]
    TOOLS --> SERVICES["Application services"]
    SERVICES --> ORM["Async SQLAlchemy"]
    ORM --> DB[("PostgreSQL via asyncpg")]
    TOOLS -->|"Command: draft + activity"| RESPONSE["Final assistant response"]
    RESPONSE -->|"message + draft_patch + tool_activity"| UI
```

## LangGraph tool-calling workflow

```mermaid
stateDiagram-v2
    [*] --> assistant
    assistant --> tools: model requests one tool
    assistant --> [*]: no tool needed
    tools --> respond
    respond --> [*]
```

1. The client sends a natural-language message and the current Redux form draft to `POST /api/chat`.
2. `run_agent` starts the LangGraph with that draft and an `AsyncSession` in graph context.
3. The `assistant` node uses LangChain's `ChatGroq` model with the five available tools.
4. `tools_condition` routes a tool call to LangGraph's `ToolNode`.
5. A tool calls the service layer, then returns a LangGraph `Command` containing a `ToolMessage`, tool activity, and optionally an updated draft.
6. The `respond` node uses the non-tool-bound model to produce a concise confirmation, then the graph ends.

The graph deliberately permits **one tool per user message**. The final response node cannot call tools, which keeps each turn bounded and prevents agent/tool recursion.

### LangChain, LangGraph, and Groq responsibilities

| Component | Responsibility |
| --- | --- |
| Groq | Hosts and runs `llama-3.3-70b-versatile`. |
| LangChain | Provides `ChatGroq`, message types, `@tool`, and `ToolRuntime`. |
| LangGraph | Holds graph state, routes tool calls, runs `ToolNode`, and merges `Command` updates. |
| FastAPI | Owns HTTP validation, request lifecycle, and the database session dependency. |

## Agent state and response contract

```mermaid
sequenceDiagram
    participant Rep as "Field representative"
    participant UI as "React / Redux"
    participant API as "FastAPI"
    participant Graph as "LangGraph"
    participant DB as "PostgreSQL"

    Rep->>UI: "Met Dr. Smith and discussed Product X efficacy"
    UI->>API: message + current interaction draft
    API->>Graph: draft + AsyncSession context
    Graph->>Graph: edit_interaction
    Graph-->>API: draft patch + tool activity + confirmation
    API-->>UI: ChatResponse
    UI->>UI: merge draft_patch into Redux form state
    Rep->>UI: "Save this interaction"
    UI->>API: completed draft
    API->>Graph: log_interaction
    Graph->>DB: validate and persist interaction
    DB-->>Graph: saved interaction ID
```

`POST /api/chat` returns:

```json
{
  "message": "Interaction saved.",
  "draft_patch": {
    "hcp_name": "Dr. Smith",
    "interaction_type": "meeting"
  },
  "tool_activity": [
    {
      "tool_name": "log_interaction",
      "summary": "Saved interaction #3"
    }
  ]
}
```

The frontend should merge `draft_patch` into the Redux form state and render `tool_activity` in the assistant panel.

## Tools

| Tool | What it does | Persistence |
| --- | --- | --- |
| `edit_interaction` | Extracts or changes structured interaction fields in the in-memory draft. | No |
| `get_hcp_profile` | Returns specialty, organization, priority, and interaction history. | No |
| `recommend_materials` | Returns approved material matched to HCP specialty and topic tags. | No |
| `create_follow_up` | Creates a dated follow-up task for an HCP. | `follow_ups` |
| `log_interaction` | Validates the complete draft and writes it with material distributions. | `interactions`, `interaction_materials` |

## Data model

```mermaid
erDiagram
    HCP ||--o{ INTERACTION : has
    HCP ||--o{ FOLLOW_UP : owns
    INTERACTION ||--o{ INTERACTION_MATERIAL : includes
    MATERIAL ||--o{ INTERACTION_MATERIAL : distributed_as
    INTERACTION ||--o{ FOLLOW_UP : may_generate

    HCP {
        int id PK
        string name
        string specialty
        string organization
        string priority
    }
    INTERACTION {
        int id PK
        int hcp_id FK
        datetime occurred_at
        string channel
        string sentiment
    }
    MATERIAL {
        int id PK
        string name
        boolean is_approved
    }
    FOLLOW_UP {
        int id PK
        int hcp_id FK
        date due_on
        string status
    }
```

## Setup

### 1. Create the database

Create a local PostgreSQL database named `hcp_crm`.

### 2. Configure environment variables

Create `server/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:URL_ENCODED_PASSWORD@localhost:5432/hcp_crm
GROQ_API_KEY=your_groq_api_key
```

URL-encode reserved characters in the password. For example, `@` becomes `%40`.

### 3. Install dependencies and run migrations

```powershell
cd server
uv sync
uv run alembic upgrade head
uv run python -m app.seed
```

The seed command creates demo data for Dr. Smith and approved Product X materials.

### 4. Start the API

```powershell
uv run uvicorn main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

## HTTP endpoints

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/chat` | Run the AI assistant against a message and draft. |
| `POST` | `/api/interactions` | Save a structured interaction without AI. |
| `GET` | `/api/hcps/{hcp_name}` | Read an HCP profile and interaction history. |
| `GET` | `/api/materials?hcp_name=...&topic=...` | Find approved material recommendations. |
| `POST` | `/api/follow-ups` | Create a follow-up without AI. |

## Demo flow

1. Seed the database and open `/docs`.
2. Send: `Met Dr. Smith today, discussed Product X efficacy, and shared a brochure.`
3. Confirm that `edit_interaction` returns a draft update.
4. Ask for Dr. Smith's profile and approved efficacy materials.
5. Create a dated follow-up.
6. Send `Save this interaction` with a complete draft using an approved material name such as `Product X Efficacy Brochure`.

## Validation and data safety

- `log_interaction` validates the draft with `InteractionCreate` before saving.
- Only approved materials can be distributed.
- Duplicate material/type distributions in one interaction are rejected.
- Database commits roll back if persistence fails.
- `.env` is intentionally not committed.
