import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.itglue_client import ITGlueClient

router = APIRouter(prefix="/migrations")


class ScanRequest(BaseModel):
    api_key: str
    org_id: str
    base_url: str | None = None


@router.post("/scan")
async def scan_organization(body: ScanRequest):
    client = ITGlueClient(
        api_key=body.api_key,
        base_url=body.base_url or settings.itglue_base_url,
    )
    try:
        documents, flexible_assets, passwords, configurations, contacts, locations = await asyncio.gather(
            client.get_documents(body.org_id),
            client.get_flexible_assets(body.org_id),
            client.get_passwords(body.org_id),
            client.get_configurations(body.org_id),
            client.get_contacts(body.org_id),
            client.get_locations(body.org_id),
        )
        return {
            "org_id": body.org_id,
            "documents": {"count": len(documents), "items": documents},
            "flexible_assets": {"count": len(flexible_assets), "items": flexible_assets},
            "passwords": {"count": len(passwords), "items": passwords},
            "configurations": {"count": len(configurations), "items": configurations},
            "contacts": {"count": len(contacts), "items": contacts},
            "locations": {"count": len(locations), "items": locations},
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
