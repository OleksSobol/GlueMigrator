from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.encryption import encrypt, decrypt
from app.db.database import get_session
from app.db import crud
from app.services.itglue_client import ITGlueClient

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialCreate(BaseModel):
    label: str
    source_api_key: str
    dest_api_key: str
    source_base_url: str = "https://api.itglue.com"
    dest_base_url: str = "https://api.itglue.com"


def _serialize(obj) -> dict:
    return {
        "id": obj.id,
        "label": obj.label,
        "source_base_url": obj.source_base_url,
        "dest_base_url": obj.dest_base_url,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
    }


@router.post("")
async def create_credential(body: CredentialCreate):
    async with get_session() as db:
        obj = await crud.create_credential(
            db=db,
            label=body.label,
            source_key_enc=encrypt(body.source_api_key),
            dest_key_enc=encrypt(body.dest_api_key),
            source_url=body.source_base_url,
            dest_url=body.dest_base_url,
        )
        return _serialize(obj)


@router.get("")
async def list_credentials():
    async with get_session() as db:
        items = await crud.list_credentials(db)
        return [_serialize(i) for i in items]


@router.get("/{credential_id}")
async def get_credential(credential_id: str):
    async with get_session() as db:
        obj = await crud.get_credential(db, credential_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Credential not found")
        return _serialize(obj)


@router.delete("/{credential_id}")
async def delete_credential(credential_id: str):
    async with get_session() as db:
        deleted = await crud.delete_credential(db, credential_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Credential not found")
        return {"deleted": True}


@router.get("/{credential_id}/organizations")
async def list_organizations(credential_id: str, side: str = "source"):
    """Fetch orgs for source or dest side of a credential."""
    async with get_session() as db:
        obj = await crud.get_credential(db, credential_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Credential not found")

    if side == "dest":
        client = ITGlueClient(api_key=decrypt(obj.dest_api_key_enc), base_url=obj.dest_base_url)
    else:
        client = ITGlueClient(api_key=decrypt(obj.source_api_key_enc), base_url=obj.source_base_url)

    try:
        orgs = await client.get_organizations()
        return orgs
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
