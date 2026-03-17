from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.itglue_client import ITGlueClient

router = APIRouter(prefix="/accounts")

class ProbeRequest(BaseModel):
    api_key:str
    base_url:str | None=None

@router.post("/probe")
async def probe_account(body: ProbeRequest):
    """Test API key"""
    client = ITGlueClient(
        api_key=body.api_key,
        base_url=body.base_url or settings.itglue_base_url
    )
    try:
        return await client.verify()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/organizations")
async def list_organizations(body: ProbeRequest):
    """Return all orgranizations for API key"""
    client = ITGlueClient(
        api_key=body.api_key,
        base_url=body.base_url or settings.itglue_base_url
    )
    try:
        orgs = await client.get_organizations()
        return {"count": len(orgs), "organizations": orgs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/org/{org_id}/documents")
async def list_documents(org_id: str, body: ProbeRequest):
    client = ITGlueClient(
        api_key=body.api_key,
        base_url=body.base_url or settings.itglue_base_url
    )
    try:
        docs = await client.get_documents(org_id)
        return {"count": len(docs), "documents": docs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/org/{org_id}/documents/{doc_id}")
async def get_document(org_id: str, doc_id: str, body: ProbeRequest):
    """Fetch full document with sections and attachments."""
    client = ITGlueClient(
        api_key=body.api_key,
        base_url=body.base_url or settings.itglue_base_url
    )
    try:
        return await client.get_document(org_id, doc_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

