import json
import asyncio

from app.db import crud
from pydantic import BaseModel
from app.core.encryption import decrypt
from app.db.database import get_session
from fastapi import APIRouter, HTTPException
from app.services.itglue_client import ITGlueClient
from app.services.migration_engine import run_migration

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    credential_id: str
    source_org_id: str
    source_org_name: str
    dest_org_id: str
    dest_org_name: str


def _serialize(obj) -> dict:
    return {
        "id": obj.id,
        "credential_id": obj.credential_id,
        "source_org_id": obj.source_org_id,
        "source_org_name": obj.source_org_name,
        "dest_org_id": obj.dest_org_id,
        "dest_org_name": obj.dest_org_name,
        "status": obj.status,
        "total_items": obj.total_items,
        "completed_items": obj.completed_items,
        "failed_items": obj.failed_items,
        "error_message": obj.error_message,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "started_at": obj.started_at.isoformat() if obj.started_at else None,
        "completed_at": obj.completed_at.isoformat() if obj.completed_at else None,
    }


@router.post("")
async def create_job(body: JobCreate):
    async with get_session() as db:
        obj = await crud.create_job(
            db=db,
            credential_id=body.credential_id,
            source_org_id=body.source_org_id,
            source_org_name=body.source_org_name,
            dest_org_id=body.dest_org_id,
            dest_org_name=body.dest_org_name,
        )
        return _serialize(obj)


@router.get("")
async def list_jobs():
    async with get_session() as db:
        items = await crud.list_jobs(db)
        return [_serialize(i) for i in items]


@router.get("/{job_id}")
async def get_job(job_id: str):
    async with get_session() as db:
        obj = await crud.get_job(db, job_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Job not found")
        return _serialize(obj)


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    async with get_session() as db:
        deleted = await crud.delete_job(db, job_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"deleted": True}


@router.post("/{job_id}/start")
async def start_job(job_id: str):
    async with get_session() as db:
        obj = await crud.get_job(db, job_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Job not found")
        if obj.status not in ("pending", "failed"):
            raise HTTPException(status_code=400, detail=f"Job cannot be started from status '{obj.status}'")
        obj.status = "queued"
        await db.commit()

    asyncio.create_task(run_migration(job_id))
    return {"status": "queued"}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    async with get_session() as db:
        obj = await crud.get_job(db, job_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Job not found")
        if obj.status not in ("pending", "queued", "running"):
            raise HTTPException(status_code=400, detail=f"Job cannot be cancelled from status '{obj.status}'")
        obj.status = "cancelled"
        await db.commit()
    return {"status": "cancelled"}


@router.get("/{job_id}/items")
async def list_job_items(job_id: str):
    async with get_session() as db:
        job = await crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        items = await crud.list_job_items(db, job_id)
        return [
            {
                "id": i.id,
                "item_type": i.item_type,
                "source_resource_name": i.source_resource_name,
                "source_resource_id": i.source_resource_id,
                "dest_resource_id": i.dest_resource_id,
                "status": i.status,
                "retry_count": i.retry_count,
                "error_message": i.error_message,
            }
            for i in items
        ]


@router.get("/{job_id}/asset-type-map")
async def get_asset_type_map(job_id: str):
    async with get_session() as db:
        job = await crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        cred = await crud.get_credential(db, job.credential_id)

    source_client = ITGlueClient(
        api_key=decrypt(cred.source_api_key_enc),
        base_url=cred.source_base_url,
    )
    dest_client = ITGlueClient(
        api_key=decrypt(cred.dest_api_key_enc),
        base_url=cred.dest_base_url,
    )

    source_types, dest_types = await asyncio.gather(
        source_client.get_flexible_asset_types(),
        dest_client.get_flexible_asset_types(),
    )

    return {
        "source_types": source_types,
        "dest_types": dest_types,
    }


class AssetTypeMapping(BaseModel):
    mappings: dict[str, str]  # source_type_id -> dest_type_id


@router.post("/{job_id}/asset-type-map")
async def save_asset_type_map(job_id: str, body: AssetTypeMapping):
    async with get_session() as db:
        job = await crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        config = await crud.create_mapping_config(
            db=db,
            label=f"Asset type map for job {job_id}",
            source_org_id=job.source_org_id,
            dest_org_id=job.dest_org_id,
            mappings=json.dumps(body.mappings),
        )
        job.mapping_config_id = config.id
        await db.commit()
    return {"mapping_config_id": config.id}
