# Agent Service — Teammate Guide

This folder is where you build the AI agent internals.
The scaffolding (registry, control API, DB, Docker) is already done.

---

## What's Already Built

| File | Status | What it does |
|---|---|---|
| `main.py` | ✅ Done | App factory, lifespan, wiring |
| `config.py` | ✅ Done | Settings from `.env` |
| `database.py` | ✅ Done | Async SQLAlchemy engine + `get_db()` |
| `control_api/routes.py` | ✅ Done | `/control/register`, `/control/heartbeat`, `/control/services` |
| `registry/models.py` | ✅ Done | `RegisteredService` ORM + Pydantic schemas |

---

## What You Need to Build

Create these files inside `services/agent/`:

```
services/agent/
└── agent/
    ├── provider.py     ← AI provider abstraction (OpenAI/Anthropic/Ollama)
    ├── tools.py        ← Tool definitions + executors (call registered services)
    ├── chat.py         ← POST /agent/chat endpoint (agentic loop)
    └── monitor.py      ← Background task watching registered services
```

---

## Reading the Registry

Every user service that registers is in the `registered_services` table.
Query it to know what services the agent can manage:

```python
from sqlalchemy import select
from registry.models import RegisteredService

async def get_active_services(db):
    result = await db.execute(
        select(RegisteredService).where(RegisteredService.is_active == True)
    )
    return result.scalars().all()

# Each service has:
# .name           → "product-service"
# .base_url       → "http://product-service:8011"
# .health_url     → "/health"
# .service_type   → "rest" | "websocket"
# .instructions   → "Alert me if error rate > 5%"  ← user's management rules
# .status         → "healthy" | "degraded" | "down"
# .last_seen      → last heartbeat timestamp
```

---

## Registering a Router

Once you build `agent/chat.py`:

```python
# In main.py, uncomment:
from agent.chat import router as chat_router
app.include_router(chat_router)
```

---

## AI Provider Config

Switch provider in `.env` — no code changes:
```env
AI_PROVIDER=openai      # or anthropic, ollama
OPENAI_API_KEY=sk-...
```

`settings.ai_provider`, `settings.openai_api_key` etc. are available in `config.py`.

---

## Control API Flow

```
User's microservice starts
        │
        ▼
POST http://agent:8000/control/register
Headers: X-Control-Key: <CONTROL_API_KEY>
Body: { name, base_url, instructions, ... }
        │
        ▼
Agent stores it in registered_services table
        │
        ▼
Service pings POST /control/heartbeat every 30s
        │
        ▼
Agent marks service DOWN if heartbeat missed for > 90s
        │
        ▼
User updates instructions via PATCH /control/services/{name}/instructions
        │
        ▼
Agent reads new instructions and adjusts behaviour
```
