# Platform

AI agent that manages user-provided microservices.

---

## Structure

```
platform/
├── .env                        ← all secrets + URLs
├── docker-compose.yml          ← spins up everything
│
├── services/
│   └── agent/                  ← THE PRODUCT (teammates build internals)
│       ├── main.py             ← app factory (wire your routers here)
│       ├── config.py           ← settings
│       ├── database.py         ← async SQLAlchemy
│       ├── control_api/
│       │   └── routes.py       ← /control/register + /heartbeat + /services
│       ├── registry/
│       │   └── models.py       ← RegisteredService ORM + schemas
│       └── TEAMMATES.md        ← guide for building agent internals
│
├── rest/                       ← Sample REST microservices
│   ├── gateway/                ← :8010 — public entry point
│   ├── product-service/        ← :8011 (internal) — catalog + inventory
│   └── payment-service/        ← :8012 (internal) — payments + refunds
│
└── ws/                         ← Sample WebSocket microservices
    ├── gateway/                ← :8020 — public entry point (HTTP + WS proxy)
    ├── metrics-service/        ← :8021 (internal) — live metrics stream
    └── chat-service/           ← :8022 (internal) — real-time chat rooms
```

---

## Public Ports

| Port | Service | Description |
|------|---------|-------------|
| 8000 | Agent | Control API + AI chat (your product) |
| 8010 | REST Gateway | Product & payment APIs |
| 8020 | WS Gateway | WebSocket + REST for metrics & chat |

All other ports are internal only (Docker network).

---

## Quick Start

```powershell
# 1. Configure secrets
copy .env .env.local   # edit with real values

# 2. Start everything
docker compose up --build

# 3. Verify
curl http://localhost:8000/health   # agent
curl http://localhost:8010/health   # REST gateway
curl http://localhost:8020/health   # WS gateway
```

---

## How Services Register with the Agent

Every sample service automatically registers on startup:

```python
# Called inside lifespan() of each service
await register_with_agent(
    name="product-service",
    base_url="http://product-service:8011",
    description="Manages product catalog and inventory.",
    instructions="Alert developer if stock drops below 10 units.",
)
```

Then it sends a heartbeat every 30s:
```
POST http://agent:8000/control/heartbeat
X-Control-Key: <CONTROL_API_KEY>
{ "name": "product-service", "status": "healthy" }
```

The agent marks any service **DOWN** if heartbeat is missed for > 90s.

---

## Control API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/control/register` | X-Control-Key | Register a service |
| POST | `/control/heartbeat` | X-Control-Key | Keep-alive ping |
| GET | `/control/services` | none | List all services |
| GET | `/control/services/{name}` | none | Get one service |
| PATCH | `/control/services/{name}/instructions` | none | Update management rules |
| DELETE | `/control/services/{name}` | X-Control-Key | Deregister |

---

## REST Service Endpoints  (via :8010)

```
GET    /api/products/                  List products
POST   /api/products/               *  Create product
GET    /api/products/{id}              Get product
PATCH  /api/products/{id}           *  Update product
POST   /api/products/{id}/stock     *  Adjust stock level
DELETE /api/products/{id}           *  Deactivate product

POST   /api/payments/               *  Create payment
GET    /api/payments/               *  My payment history
GET    /api/payments/{id}           *  Get payment
POST   /api/payments/{id}/refund    *  Refund payment

* = requires Authorization: Bearer <JWT>
```

---

## WebSocket Endpoints  (via :8020)

```
# Live metrics dashboard
WS  ws://localhost:8020/ws/metrics
    → send:    { "subscribe": ["product-service", "payment-service"] }
    → receive: { "type": "metric", "service": "...", "cpu": 12.3, ... }

# Live chat
WS  ws://localhost:8020/ws/chat/{room_id}?token=<JWT>
    → send:    { "content": "Hello!" }
    → receive: { "type": "message", "sender_name": "...", "content": "..." }

# REST: create/list chat rooms
POST GET  /api/rooms
GET       /api/rooms/{id}/history

# REST: ingest metrics (called by services)
POST      /metrics
GET       /metrics/{service_name}
```

---

## Adding a New Service

1. Build your service with `main.py`, `models.py`, `routes.py`, `database.py`
2. Add agent registration in lifespan:
   ```python
   await register_with_agent(name=..., base_url=..., description=..., instructions=...)
   ```
3. Add to `docker-compose.yml` (REST or WS section)
4. Add its route to the appropriate gateway

---

## Teammates — See `services/agent/TEAMMATES.md`
