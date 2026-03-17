from sqlalchemy.ext.asyncio  import AsyncSession
from sqlalchemy import select
from app.db.models import ApiCredential, MigrationJob, MigrationJobItem, MappingConfig

# --- ApiCredential ---
async def create_credential(
        db: AsyncSession, 
        label: str, 
        source_key_enc: str, 
        dest_key_enc: str, 
        source_url: str, 
        dest_url) -> ApiCredential:
    
    obj = ApiCredential(
        label=label, 
        source_api_key_enc=source_key_enc,
        dest_api_key_enc=dest_key_enc,
        source_base_url=source_url,
        dest_base_url=dest_url,
    )

    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    return obj

async def get_credential(db: AsyncSession, credential_id: str) -> ApiCredential | None:
    result = await db.execute(select(ApiCredential).where(ApiCredential.id == credential_id))
    return result.scalar_one_or_none()

async def list_credentials(db: AsyncSession) -> list[ApiCredential]:
    result = await db.execute(select(ApiCredential))
    return result.scalars().all()

async def delete_credential(db: AsyncSession, credential_id: str) -> bool:
    obj = await get_credential(db, credential_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True

# --- MigrationJob ---
async def create_job(
        db: AsyncSession,
        credential_id: str,
        source_org_id: str,
        source_org_name: str,
        dest_org_id: str,
        dest_org_name: str,
        status: str = "pending",
) -> MigrationJob:
    obj = MigrationJob(
        credential_id=credential_id,
        source_org_id=source_org_id,
        source_org_name=source_org_name,
        dest_org_id=dest_org_id,
        dest_org_name=dest_org_name,
        status=status,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_job(db: AsyncSession, job_id: str) -> MigrationJob | None:
    result = await db.execute(select(MigrationJob).where(MigrationJob.id == job_id))
    return result.scalar_one_or_none()

async def list_jobs(db: AsyncSession) -> list[MigrationJob]:
    result = await db.execute(select(MigrationJob))
    return result.scalars().all()

async def delete_job(db: AsyncSession, job_id: str) -> bool:
    obj = await get_job(db, job_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True

# --- MigrationJobItem ---
async def create_job_item(
        db: AsyncSession,
        job_id: str,
        item_type: str,
        source_resource_id: str,
        source_resource_name: str,
        parent_item_id: str | None = None,
) -> MigrationJobItem:
    obj = MigrationJobItem(
        job_id=job_id,
        item_type=item_type,
        source_resource_id=source_resource_id,
        source_resource_name=source_resource_name,
        parent_item_id=parent_item_id,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_job_item(db: AsyncSession, item_id: str) -> MigrationJobItem | None:
    result = await db.execute(select(MigrationJobItem).where(MigrationJobItem.id == item_id))
    return result.scalar_one_or_none()

async def list_job_items(db: AsyncSession, job_id: str) -> list[MigrationJobItem]:
    result = await db.execute(select(MigrationJobItem).where(MigrationJobItem.job_id == job_id))
    return result.scalars().all()

async def delete_job_item(db: AsyncSession, item_id: str) -> bool:
    obj = await get_job_item(db, item_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True

# --- MappingConfig ---
async def create_mapping_config(
        db: AsyncSession,
        label: str,
        source_org_id: str,
        dest_org_id: str,
        mappings: str,
) -> MappingConfig:
    obj = MappingConfig(
        label=label,
        source_org_id=source_org_id,
        dest_org_id=dest_org_id,
        mappings=mappings,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_mapping_config(db: AsyncSession, config_id: str) -> MappingConfig | None:
    result = await db.execute(select(MappingConfig).where(MappingConfig.id == config_id))
    return result.scalar_one_or_none()

async def list_mapping_configs(db: AsyncSession) -> list[MappingConfig]:
    result = await db.execute(select(MappingConfig))
    return result.scalars().all()

async def delete_mapping_config(db: AsyncSession, config_id: str) -> bool:
    obj = await get_mapping_config(db, config_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True


