import asyncio
import json

from app.db.database import get_session
from app.db import crud
from app.services.itglue_client import ITGlueClient
from app.core.encryption import decrypt


async def run_migration(job_id: str):
    async with get_session() as db:
        job = await crud.get_job(db, job_id)
        if not job:
            return

        cred = await crud.get_credential(db, job.credential_id)
        source_client = ITGlueClient(
            api_key=decrypt(cred.source_api_key_enc),
            base_url=cred.source_base_url,
        )
        dest_client = ITGlueClient(
            api_key=decrypt(cred.dest_api_key_enc),
            base_url=cred.dest_base_url,
        )

        job.status = "running"
        await db.commit()

        # Scan source org concurrently
        documents, passwords, flexible_assets, configurations, contacts, locations = await asyncio.gather(
            source_client.get_documents(job.source_org_id),
            source_client.get_passwords(job.source_org_id),
            source_client.get_flexible_assets(job.source_org_id),
            source_client.get_configurations(job.source_org_id),
            source_client.get_contacts(job.source_org_id),
            source_client.get_locations(job.source_org_id),
        )

        all_items = (
            [("document", d) for d in documents] +
            [("password", p) for p in passwords] +
            [("flexible_asset", f) for f in flexible_assets] +
            [("configuration", c) for c in configurations] +
            [("contact", c) for c in contacts] +
            [("location", l) for l in locations]
        )

        # Create a job item row for every resource found
        for item_type, resource in all_items:
            await crud.create_job_item(
                db=db,
                job_id=job.id,
                item_type=item_type,
                source_resource_id=resource["id"],
                source_resource_name=resource.get("name", ""),
            )

        job.total_items = len(all_items)
        await db.commit()

        # Migrate each item
        for item_type, resource in all_items:
            await db.refresh(job)
            if job.status == "cancelled":
                return
            await _migrate_item(db, job, item_type, resource, source_client, dest_client)

        # Set final status
        await db.refresh(job)
        if job.status == "cancelled":
            return
        if job.failed_items == 0:
            job.status = "completed"
        elif job.completed_items == 0:
            job.status = "failed"
        else:
            job.status = "partially_complete"
        await db.commit()


async def _migrate_item(db, job, item_type, resource, source_client, dest_client):
    items = await crud.list_job_items(db, job.id)
    item = next((i for i in items if i.source_resource_id == resource["id"]), None)
    if not item:
        return

    item.status = "in_progress"
    await db.commit()

    try:
        if item_type == "document":
            full = await source_client.get_document(job.source_org_id, resource["id"])
            payload = {"data": {"type": "documents", "attributes": {
                "name": full["name"],
                "content": full.get("sections", []),
            }}}
            created = await dest_client.create_document(job.dest_org_id, payload)
            item.dest_resource_id = created["id"]

        elif item_type == "password":
            full = await source_client.get_password(resource["id"])
            payload = {"data": {"type": "passwords", "attributes": {
                "name": full["name"],
                "username": full.get("username"),
                "password": full.get("password"),
                "url": full.get("url"),
                "notes": full.get("notes"),
            }}}
            created = await dest_client.create_password(job.dest_org_id, payload)
            item.dest_resource_id = created["id"]

        elif item_type == "configuration":
            payload = {"data": {"type": "configurations", "attributes": {
                "name": resource["name"],
                "hostname": resource.get("hostname"),
                "primary-ip": resource.get("ip_address"),
                "serial-number": resource.get("serial_number"),
            }}}
            created = await dest_client.create_configuration(job.dest_org_id, payload)
            item.dest_resource_id = created["id"]

        elif item_type == "contact":
            payload = {"data": {"type": "contacts", "attributes": {
                "first-name": resource.get("first_name"),
                "last-name": resource.get("last_name"),
                "title": resource.get("title"),
            }}}
            created = await dest_client.create_contact(job.dest_org_id, payload)
            item.dest_resource_id = created["id"]

        elif item_type == "location":
            payload = {"data": {"type": "locations", "attributes": {
                "name": resource["name"],
                "primary": resource.get("primary"),
                "address-1": resource.get("address_1"),
                "address-2": resource.get("address_2"),
                "city": resource.get("city"),
                "region-name": resource.get("region_name"),
                "postal-code": resource.get("postal_code"),
                "country-name": resource.get("country_name"),
                "phone": resource.get("phone"),
            }}}
            created = await dest_client.create_location(job.dest_org_id, payload)
            item.dest_resource_id = created["id"]

        elif item_type == "flexible_asset":
            if not job.mapping_config_id:
                item.status = "skipped"
                await db.commit()
                return
            mapping_config = await crud.get_mapping_config(db, job.mapping_config_id)
            mappings = json.loads(mapping_config.mappings)
            dest_type_id = mappings.get(resource.get("type_id") or resource.get("flexible_asset_type_id"))
            if not dest_type_id:
                item.status = "skipped"
                await db.commit()
                return
            full = await source_client.get_flexible_asset(resource["id"])
            payload = {"data": {"type": "flexible_assets", "attributes": {
                "name": full["name"],
                "flexible-asset-type-id": dest_type_id,
                "organization-id": job.dest_org_id,
                "traits": full.get("traits", {}),
            }}}
            created = await dest_client.create_flexible_asset(payload)
            item.dest_resource_id = created["id"]

        item.status = "completed"
        job.completed_items += 1

    except Exception as e:
        item.status = "failed"
        item.error_message = str(e)
        item.retry_count += 1
        job.failed_items += 1
        job.error_message = str(e)

    await db.commit()
