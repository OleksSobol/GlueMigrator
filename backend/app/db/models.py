import uuid

from typing import Optional
from enum import Enum as PyEnum
from app.db.database import Base
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Enum


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4())) 
    label: Mapped[str] = mapped_column(String)
    source_api_key_enc: Mapped[str] = mapped_column(String)
    dest_api_key_enc: Mapped[str] = mapped_column(String)
    source_base_url: Mapped[str] = mapped_column(String)
    dest_base_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
class JobStatus(str, PyEnum):
    PENDING = "pending"
    SCANNING = "scanning"
    SCAN_COMPLETE = "scan_complete"
    SCAN_FAILED = "scan_failed"
    MAPPING_REQUIRED = "mapping_required"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETE = "partially_complete"
    CANCELLED = "cancelled"
    FAILED = "failed"

class MigrationJob(Base):
    __tablename__ = "migration_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    credential_id: Mapped[str] = mapped_column(String)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_org_id: Mapped[str] = mapped_column(String)
    source_org_name: Mapped[str] = mapped_column(String)
    dest_org_id: Mapped[str] = mapped_column(String)
    dest_org_name: Mapped[str] = mapped_column(String)
    mapping_config_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    scan_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ItemType(str, PyEnum):
    DOCUMENT = "document"
    PASSWORD = "password"
    FLEXIBLE_ASSET = "flexible_asset"
    CONFIGURATION = "configuration"
    CONTACT = "contact"
    LOCATION = "location"
    ATTACHMENT = "attachment"

class ItemStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class MigrationJobItem(Base):
    __tablename__ = "migration_job_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("migration_jobs.id"))
    item_type: Mapped[str] = mapped_column(String)
    source_resource_id: Mapped[str] = mapped_column(String)
    source_resource_name: Mapped[str] = mapped_column(String)
    parent_item_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("migration_job_items.id"), nullable=True)
    dest_resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class MappingConfig(Base):
    __tablename__ = "mapping_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    label: Mapped[str] = mapped_column(String)
    source_org_id: Mapped[str] = mapped_column(String)
    dest_org_id: Mapped[str] = mapped_column(String)
    mappings: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

