# SaaS Platform — Microservices Starter

A production-ready Python microservices foundation with 3 services, separate databases, async messaging, and file storage.

## Architecture

```
Internet
   │
[Traefik API Gateway :80]
   │
   ├── /api/auth/*     → User Service (FastAPI) → PostgreSQL (users_db)
   ├── /api/users/*    → User Service (FastAPI) → PostgreSQL (users_db)
   ├── /api/files/*    → File Service (FastAPI) → PostgreSQL (files_db) + MinIO
   └── /api/notifications/* → Notification Service (FastAPI) → PostgreSQL (notifications_db)

Async Events via RabbitMQ:
  User Service ──publishes──▶ [user_events exchange]
  File Service ──publishes──▶ [file_events exchange]
                                        │
                              Notification Service (consumer)
                              sends email/SMS automatically
```

## Services

| Service | Port (internal) | Database | Responsibility |
|---|---|---|---|
| user-service | 8000 | users_db | Registration, login, JWT, profiles |
| notification-service | 8000 | notifications_db | Email (SMTP), SMS (Twilio), event-driven |
| file-service | 8000 | files_db | Upload, store (MinIO), presigned URLs |

## Infrastructure

| Tool | Purpose | Dashboard |
|---|---|---|
| Traefik | API Gateway + routing | http://localhost:8080 |
| PostgreSQL x3 | One DB per service | — |
| Redis | Caching, sessions | — |
| RabbitMQ | Async event bus | http://localhost:15672 (saas/saas_password) |
| MinIO | S3-compatible file storage | http://localhost:9001 (saas_minio/saas_minio_password) |

## Quick Start

### 1. Clone and configure
```bash
cp .env.example .env
# Edit .env with your SMTP credentials (optional for local dev)
```

### 2. Start everything
```bash
docker compose up --build
```

### 3. Check services are healthy
```bash
curl http://localhost/api/auth/health    # User service via gateway
curl http://localhost/api/files/health   # File service via gateway
```

### 4. Register a user
```bash
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "username": "yourname",
    "full_name": "Your Name",
    "password": "securepassword"
  }'
```

### 5. Login and get token
```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepassword"}'
```

### 6. Upload a file (use token from login)
```bash
curl -X POST http://localhost/api/files/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/yourfile.pdf"
```

## API Docs (Swagger)

Each service auto-generates interactive API docs. Access directly (bypass gateway):

> In development, temporarily expose service ports in docker-compose for direct access.

- User Service: http://localhost:8001/docs
- Notification Service: http://localhost:8002/docs
- File Service: http://localhost:8003/docs

To expose ports for dev, add to each service in docker-compose.yml:
```yaml
ports:
  - "8001:8000"  # user-service
```

## Key API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | /api/auth/register | Create account |
| POST | /api/auth/login | Login, get JWT |
| POST | /api/auth/refresh | Refresh access token |
| POST | /api/auth/logout | Revoke refresh token |

### Users
| Method | Path | Description |
|---|---|---|
| GET | /api/users/me | Get current user + subscription |
| PATCH | /api/users/me | Update profile |
| POST | /api/users/me/change-password | Change password |

### Files
| Method | Path | Description |
|---|---|---|
| POST | /api/files/upload | Upload a file |
| GET | /api/files/ | List your files |
| GET | /api/files/{id}/download-url | Get presigned download URL |
| DELETE | /api/files/{id} | Soft-delete a file |

### Notifications
| Method | Path | Description |
|---|---|---|
| POST | /api/notifications/send | Manually trigger notification |
| GET | /api/notifications/logs/{user_id} | View notification history |

## Event Flow

When a user registers:
1. User Service creates user + saves to `users_db`
2. User Service publishes `user.registered` event to RabbitMQ
3. Notification Service receives event automatically
4. Notification Service sends welcome email
5. Notification log saved to `notifications_db`

When a file is uploaded:
1. File Service stores file in MinIO
2. File Service saves metadata to `files_db`
3. (Optional) Publish `file.uploaded` event → welcome email with file info

## Database Migrations

Each service uses Alembic for migrations. Run inside the container:

```bash
# User service
docker compose exec user-service alembic revision --autogenerate -m "add column"
docker compose exec user-service alembic upgrade head

# File service
docker compose exec file-service alembic revision --autogenerate -m "add column"
docker compose exec file-service alembic upgrade head
```

## Adding a New Microservice

1. Copy `services/user-service` as a template
2. Add to `docker-compose.yml` with its own Postgres instance
3. Add Traefik label for routing
4. Wire up RabbitMQ events as needed

## Production Checklist

- [ ] Change `SECRET_KEY` to a real random value
- [ ] Set real SMTP credentials
- [ ] Set `CORS` origins to your actual domain
- [ ] Enable HTTPS in Traefik (Let's Encrypt)
- [ ] Use Docker secrets or a vault for credentials
- [ ] Set up Grafana + Prometheus for monitoring
- [ ] Configure database backups
- [ ] Add Stripe billing service
