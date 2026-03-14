# GlueMigrator

A migration tool for MSPs to move data between IT Glue organizations. Handles documents, flexible assets, and attachments — including structural differences between source and destination accounts.

## Stack

- **Backend** — FastAPI (Python 3.13), async httpx, SQLite
- **Frontend** — Astro + Tailwind CSS *(coming soon)*

## Project Structure

```
GlueMigrator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── core/
│   │   │   └── config.py        # Settings (pydantic-settings)
│   │   ├── api/v1/
│   │   │   ├── health.py        # GET /api/v1/health
│   │   │   ├── accounts.py      # API key management + org listing
│   │   │   └── migrations.py    # Scan + migration jobs
│   │   └── services/
│   │       └── itglue_client.py # IT Glue API client
│   ├── pyproject.toml
│   └── .env
└── frontend/                    # coming soon
```

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)

### Backend Setup

```bash
cd backend
uv sync
cp .env.example .env   # add your IT Glue API key
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

### Environment Variables

```env
ITGLUE_BASE_URL=https://api.itglue.com
```

## API Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |

### Accounts
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/accounts/probe` | Verify an IT Glue API key |
| POST | `/api/v1/accounts/organizations` | List all organizations for an API key |
| POST | `/api/v1/accounts/org/{org_id}/documents` | List documents for an organization |

### Migrations
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/migrations/scan` | Scan an organization (documents + flexible assets) |

## IT Glue API Notes

- Auth header: `x-api-key`
- Content type: `application/vnd.api+json` (JSON:API)
- Rate limit: ~10 req/s — client handles 429 with `Retry-After` backoff
- Pagination: `links.next` cursor, default page size 50
- Documents: nested under `/organizations/{id}/relationships/documents`
- Flexible assets: global `/flexible_assets` endpoint with `filter[organization_id]` + `filter[flexible_asset_type_id]` (both required)
