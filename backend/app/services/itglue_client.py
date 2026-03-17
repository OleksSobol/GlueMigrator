import asyncio
import httpx

BASE_HEADERS = {
    "content-type": "application/vnd.api+json",
    "accept": "application/vnd.api+json",
}
PAGE_SIZE = 1000  # IT Glue max


class ITGlueClient:
    def __init__(self, api_key: str, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {**BASE_HEADERS, "x-api-key": api_key}

    # --- Core HTTP --

    async def _request(self, method: str, path: str, params: dict = None, payload: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(headers=self.headers, timeout=60) as client:
            for attempt in range(3):
                resp = await client.request(method, url, params=params, json=payload)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 10))
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError("Exceeded retry limit due to rate limiting")

    async def _paginate(self, path: str, params: dict = None) -> list[dict]:
        """Fetch all pages and return the raw data array."""
        results = []
        page = 1
        base_params = {**(params or {}), "page[size]": PAGE_SIZE}
        while True:
            data = await self._request("GET", path, {**base_params, "page[number]": page})
            results.extend(data.get("data", []))
            if not data.get("links", {}).get("next"):
                break
            page += 1
        return results

    # --- Account ---

    async def verify(self) -> dict:
        data = await self._request("GET", "/organizations", {"page[size]": 1, "page[number]": 1})
        return {"total_organizations": data.get("meta", {}).get("total-count", 0)}

    async def get_organizations(self) -> list[dict]:
        items = await self._paginate("/organizations")
        return [self._parse_org(i) for i in items]

    # --- Documents ---

    async def get_documents(self, org_id: str) -> list[dict]:
        items = await self._paginate(f"/organizations/{org_id}/relationships/documents")
        return [self._parse_document_summary(i) for i in items]

    async def get_document(self, org_id: str, doc_id: str) -> dict:
        data = await self._request("GET", f"/organizations/{org_id}/relationships/documents/{doc_id}")
        item = data.get("data", {})
        result = self._parse_document_summary(item)
        result["sections"] = item.get("attributes", {}).get("sections", [])
        result["attachments"] = await self.get_attachments("documents", doc_id)
        return result

    async def create_document(self, org_id: str, payload: dict) -> dict:
        data = await self._request("POST", f"/organizations/{org_id}/relationships/documents", payload=payload)
        return data.get("data", {})

    # --- Passwords ---

    async def get_passwords(self, org_id: str) -> list[dict]:
        items = await self._paginate(f"/organizations/{org_id}/relationships/passwords")
        return [self._parse_password(i) for i in items]

    async def get_password(self, password_id: str) -> dict:
        """Fetch single password including the actual password value."""
        data = await self._request("GET", f"/passwords/{password_id}", {"show_password": "true"})
        return self._parse_password(data.get("data", {}), include_value=True)

    async def create_password(self, org_id: str, payload: dict) -> dict:
        data = await self._request("POST", f"/organizations/{org_id}/relationships/passwords", payload=payload)
        return data.get("data", {})

    # --- Flexible Assets ---

    async def get_flexible_asset_types(self) -> list[dict]:
        items = await self._paginate("/flexible_asset_types")
        return [self._parse_flexible_asset_type(i) for i in items]

    async def get_flexible_assets(self, org_id: str) -> list[dict]:
        types = await self.get_flexible_asset_types()
        results = []
        for asset_type in types:
            items = await self._paginate("/flexible_assets", {
                "filter[organization_id]": org_id,
                "filter[flexible_asset_type_id]": asset_type["id"],
            })
            for item in items:
                parsed = self._parse_flexible_asset(item)
                parsed["type_id"] = asset_type["id"]
                parsed["type_name"] = asset_type["name"]
                results.append(parsed)
        return results

    async def get_flexible_asset(self, asset_id: str) -> dict:
        data = await self._request("GET", f"/flexible_assets/{asset_id}")
        item = data.get("data", {})
        parsed = self._parse_flexible_asset(item)
        parsed["traits"] = item.get("attributes", {}).get("traits", {})
        parsed["attachments"] = await self.get_attachments("flexible_assets", asset_id)
        return parsed

    async def create_flexible_asset(self, payload: dict) -> dict:
        data = await self._request("POST", "/flexible_assets", payload=payload)
        return data.get("data", {})

    # --- Configurations ---

    async def get_configurations(self, org_id: str) -> list[dict]:
        items = await self._paginate(f"/organizations/{org_id}/relationships/configurations")
        return [self._parse_configuration(i) for i in items]

    async def create_configuration(self, org_id: str, payload: dict) -> dict:
        data = await self._request("POST", f"/organizations/{org_id}/relationships/configurations", payload=payload)
        return data.get("data", {})

    # --- Contacts ---

    async def get_contacts(self, org_id: str) -> list[dict]:
        items = await self._paginate(f"/organizations/{org_id}/relationships/contacts")
        return [self._parse_contact(i) for i in items]

    async def create_contact(self, org_id: str, payload: dict) -> dict:
        data = await self._request("POST", f"/organizations/{org_id}/relationships/contacts", payload=payload)
        return data.get("data", {})

    # --- Locations ---

    async def get_locations(self, org_id: str) -> list[dict]:
        items = await self._paginate(f"/organizations/{org_id}/relationships/locations")
        return [self._parse_location(i) for i in items]

    async def create_location(self, org_id: str, payload: dict) -> dict:
        data = await self._request("POST", f"/organizations/{org_id}/relationships/locations", payload=payload)
        return data.get("data", {})

    # --- Attachments (universal) ---

    async def get_attachments(self, resource_type: str, resource_id: str) -> list[dict]:
        """
        resource_type: documents | passwords | flexible_assets | configurations |
                       contacts | locations | domains | ssl_certificates | tickets
        """
        items = await self._paginate(f"/{resource_type}/{resource_id}/relationships/attachments")
        return [self._parse_attachment(i) for i in items]

    async def upload_attachment(
        self,
        resource_type: str,
        resource_id: str,
        filename: str,
        content_type: str,
        file_bytes: bytes,
    ) -> dict:
        url = f"{self.base_url}/{resource_type}/{resource_id}/relationships/attachments"
        upload_headers = {"x-api-key": self.headers["x-api-key"]}
        async with httpx.AsyncClient(headers=upload_headers, timeout=120) as client:
            resp = await client.post(
                url,
                files={"attachment[attachment]": (filename, file_bytes, content_type)},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    # --- Parsers ---

    def _parse_org(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("name"),
            "status": a.get("organization-status-name"),
            "type": a.get("organization-type-name"),
        }

    def _parse_document_summary(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("name"),
            "document_folder_id": a.get("document-folder-id"),
            "is_uploaded": a.get("is-uploaded"),
            "archived": a.get("archived"),
            "restricted": a.get("restricted"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }

    def _parse_password(self, item: dict, include_value: bool = False) -> dict:
        a = item.get("attributes", {})
        result = {
            "id": item["id"],
            "name": a.get("name"),
            "username": a.get("username"),
            "url": a.get("url"),
            "notes": a.get("notes"),
            "password_category_id": a.get("password-category-id"),
            "password_category_name": a.get("password-category-name"),
            "resource_id": a.get("resource-id"),
            "resource_type": a.get("resource-type"),
            "archived": a.get("archived"),
            "restricted": a.get("restricted"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }
        if include_value:
            result["password"] = a.get("password")
        return result

    def _parse_flexible_asset_type(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("name"),
            "icon": a.get("icon"),
            "fields": [
                {
                    "id": f["id"],
                    "name": f["attributes"].get("name"),
                    "kind": f["attributes"].get("kind"),
                    "required": f["attributes"].get("required"),
                    "tag_type": f["attributes"].get("tag-type"),
                }
                for f in a.get("flexible-asset-fields", [])
            ] if a.get("flexible-asset-fields") else [],
        }

    def _parse_flexible_asset(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("name"),
            "flexible_asset_type_id": a.get("flexible-asset-type-id"),
            "organization_id": a.get("organization-id"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }

    def _parse_configuration(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("name"),
            "hostname": a.get("hostname"),
            "ip_address": a.get("primary-ip"),
            "configuration_type_id": a.get("configuration-type-id"),
            "configuration_type_name": a.get("configuration-type-name"),
            "configuration_status_id": a.get("configuration-status-id"),
            "configuration_status_name": a.get("configuration-status-name"),
            "manufacturer_id": a.get("manufacturer-id"),
            "manufacturer_name": a.get("manufacturer-name"),
            "model_id": a.get("model-id"),
            "model_name": a.get("model-name"),
            "serial_number": a.get("serial-number"),
            "archived": a.get("archived"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }

    def _parse_contact(self, item: dict) -> dict:
        a = item.get("attributes", {})
        emails = a.get("contact-emails") or []
        phones = a.get("contact-phones") or []
        return {
            "id": item["id"],
            "name": a.get("name"),
            "first_name": a.get("first-name"),
            "last_name": a.get("last-name"),
            "title": a.get("title"),
            "email": emails[0].get("value") if emails else None,
            "phone": phones[0].get("value") if phones else None,
            "location_id": a.get("location-id"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }

    def _parse_location(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("name"),
            "primary": a.get("primary"),
            "address_1": a.get("address-1"),
            "address_2": a.get("address-2"),
            "city": a.get("city"),
            "region_name": a.get("region-name"),
            "postal_code": a.get("postal-code"),
            "country_name": a.get("country-name"),
            "phone": a.get("phone"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }

    def _parse_attachment(self, item: dict) -> dict:
        a = item.get("attributes", {})
        return {
            "id": item["id"],
            "name": a.get("attachment-file-name") or a.get("name"),
            "content_type": a.get("attachment-content-type"),
            "size": a.get("attachment-file-size"),
            "download_url": a.get("download-url"),
            "created_at": a.get("created-at"),
            "updated_at": a.get("updated-at"),
        }
