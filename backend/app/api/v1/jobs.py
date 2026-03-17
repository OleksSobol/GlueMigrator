from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.database import get_session
from app.db import crud

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
