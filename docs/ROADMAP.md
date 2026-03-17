# GlueMigrator — Project Roadmap

## What's Done

- FastAPI app skeleton (`main.py`, CORS, router setup)
- `core/config.py` — pydantic-settings with `.env` loading
- `services/itglue_client.py` — full IT Glue API client (rewritten):
  - `_request` + `_paginate` — core HTTP with retry, 429 backoff, pagination
  - Read: `get_organizations`, `get_documents`, `get_document`, `get_passwords`, `get_password`, `get_flexible_asset_types`, `get_flexible_assets`, `get_flexible_asset`, `get_configurations`, `get_contacts`, `get_locations`, `get_attachments`
  - Write: `create_document`, `create_password`, `create_flexible_asset`, `create_configuration`, `upload_attachment`
  - Parsers for all resource types
- `api/v1/health.py` — `GET /api/v1/health`
- `api/v1/accounts.py` — probe, list orgs, list/get documents (stateless, key in body)
- `api/v1/migrations.py` — `POST /scan` (fetches all 6 resource types concurrently)
- `README.md`, `.gitignore`, pushed to GitHub

---

## What's Left

### Phase 1 — DB Layer
**You write:** create `backend/app/db/` directory with these files:

**`database.py`** — SQLAlchemy async engine + session factory
```
- async engine pointing to SQLite file at data/gluemigrator.db
- async_sessionmaker
- Base = declarative_base()
- init_db() function that creates all tables on startup
```

**`models.py`** — 4 ORM models
```
- ApiCredential   id(UUID), label, source_api_key_enc, dest_api_key_enc,
                  source_base_url, dest_base_url, created_at
- MigrationJob    id(UUID), credential_id(FK), source_org_id/name,
                  dest_org_id/name, mapping_config_id(FK nullable),
                  status(Enum), scan_data(JSON text),
                  total/completed/failed_items, error_message,
                  created/started/completed_at
- MigrationJobItem id(UUID), job_id(FK), item_type(Enum: document/password/
                   flexible_asset/configuration/contact/location/attachment),
                   source_resource_id/name, parent_item_id(FK self nullable),
                   dest_resource_id, status(Enum), retry_count
- MappingConfig   id(UUID), label, source_org_id, dest_org_id, mappings(JSON text)
```

**`crud.py`** — DB operations (create/get/list/delete for each model)

Add to `pyproject.toml`:
```
sqlalchemy[asyncio]>=2.0
aiosqlite>=0.20
cryptography>=42.0
```

Update `main.py` lifespan to call `init_db()` on startup.

---

### Phase 2 — Credential Management + Security
**You write:** `core/security.py` + rewrite `api/v1/accounts.py`

**`core/security.py`**
```
- Uses Fernet (from cryptography package)
- ENCRYPTION_KEY loaded from settings
- encrypt(plaintext: str) -> str
- decrypt(ciphertext: str) -> str
```

Add `ENCRYPTION_KEY` to `.env` (generate with `Fernet.generate_key()`)

**Rewrite `api/v1/accounts.py`** — replace stateless endpoints with DB-backed:
```
POST   /api/v1/accounts                              save credential pair (encrypt keys)
GET    /api/v1/accounts                              list saved credentials (never return keys)
DELETE /api/v1/accounts/{id}
POST   /api/v1/accounts/{id}/verify                  test both keys live
GET    /api/v1/accounts/{id}/source/organizations
GET    /api/v1/accounts/{id}/dest/organizations
GET    /api/v1/accounts/{id}/dest/flexible-asset-types
```

---

### Phase 3 — Migration Jobs API
**You write:** extend `api/v1/migrations.py` with job CRUD + scan-to-job flow

```
POST   /api/v1/migrations/scan             (update: save result to DB as job in SCANNING state)
GET    /api/v1/migrations/scan/{scan_id}   poll scan status

POST   /api/v1/migrations/jobs             create job from scan result + mapping config
GET    /api/v1/migrations/jobs             list jobs
GET    /api/v1/migrations/jobs/{id}        job detail + item counts
DELETE /api/v1/migrations/jobs/{id}        cancel
GET    /api/v1/migrations/jobs/{id}/items  ?status=failed
```

---

### Phase 4 — Migration Engine
**You write:** `services/migration_run.py` + `workers/runner.py`

**`services/migration_run.py`** — the actual copy logic per item type:
```
migrate_document(src_client, dst_client, job_item, org_ids)
  1. get_document(src_org, doc_id) → fetch full content + attachments
  2. create_document(dst_org, payload) → create in destination
  3. for each attachment: download bytes → upload_attachment to new doc
  4. mark item completed / failed

migrate_password(src_client, dst_client, job_item, org_ids)
  1. get_password(password_id, show_password=true)
  2. create_password(dst_org, payload)

migrate_flexible_asset(src_client, dst_client, job_item, mapping_config, org_ids)
  1. get_flexible_asset(asset_id) → get traits
  2. apply field mapping (source field IDs → dest field IDs)
  3. create_flexible_asset(dst_org, mapped_payload)
```

**`workers/runner.py`** — background job executor:
```
- FastAPI BackgroundTasks kicks off run_migration_job(job_id)
- Iterates job items, calls migrate_* per type
- Updates item status in DB after each
- Broadcasts progress via app.state.progress_queues[job_id]
```

**`GET /api/v1/migrations/jobs/{id}/progress/stream`** — SSE endpoint

---

### Phase 5 — Mapping Configs
**You write:** CRUD endpoints for `MappingConfig` model

```
POST   /api/v1/migrations/mappings
GET    /api/v1/migrations/mappings
GET    /api/v1/migrations/mappings/{id}
PUT    /api/v1/migrations/mappings/{id}
DELETE /api/v1/migrations/mappings/{id}
```

Mapping rule shape (stored as JSON in `mappings` column):
```json
{
  "rule_type": "flexible_asset_type",
  "source_type_id": "12345",
  "dest_type_id": "67890",
  "field_mappings": [
    {"source_field_id": "f1", "dest_field_id": "f9"}
  ]
}
```

---

### Phase 6 — Frontend
Astro + Tailwind scaffold in `frontend/`
- 5-step wizard: Connect → Select Orgs → Scan → Map Fields → Confirm + Execute
- Job detail/progress page (SSE consumer)
- Settings page (saved credential pairs)

### Phase 7 — Docker
- `backend/Dockerfile`, `frontend/Dockerfile`
- `docker-compose.yml` + `docker-compose.dev.yml`

---

## Resources Being Migrated

| Resource | Read method | Write method | Notes |
|---|---|---|---|
| Documents | `get_document` | `create_document` | sections + attachments |
| Passwords | `get_password` | `create_password` | requires `show_password=true` |
| Flexible Assets | `get_flexible_asset` | `create_flexible_asset` | field mapping required |
| Configurations | `get_configurations` | `create_configuration` | list only for now |
| Contacts | `get_contacts` | — | TBD |
| Locations | `get_locations` | — | TBD |
| Attachments | `get_attachments` | `upload_attachment` | on every resource |

## Job State Machine

```
PENDING → SCANNING → SCAN_COMPLETE → QUEUED → RUNNING → COMPLETED
                ↓               ↓                  ↓
          SCAN_FAILED   MAPPING_REQUIRED    PARTIALLY_COMPLETE
                                                       ↑
                                                   CANCELLED
```

## IT Glue API Notes

- Auth header: `x-api-key`
- Content type: `application/vnd.api+json`
- Page size: up to 1,000 (we use max)
- Rate limit: 3,000 req / 5 min window (~10/sec)
- Documents: nested under `/organizations/{id}/relationships/documents`
- Flexible assets: global `/flexible_assets` with BOTH `filter[organization_id]` AND `filter[flexible_asset_type_id]` required
- Passwords: list endpoint does NOT return password value — need `GET /passwords/{id}?show_password=true`
- Attachments: `GET /{resource_type}/{id}/relationships/attachments` — works for all resource types
