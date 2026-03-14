import asyncio
import httpx

BASE_HEADERS = {"content-type": "application/vnd.api+json"}
PAGE_SIZE = 50

class ITGlueClient:
    def __init__(self, api_key: str, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {**BASE_HEADERS, "x-api-key": api_key}

    async def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            for attempt in range(3):
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 10))
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError("Exceeded retry limit due to rate limiting")

    async def get_organizations(self) -> list[dict]:
        results = []
        page = 1
        while True:
            data = await self._get("/organizations", {"page[size]": PAGE_SIZE, "page[number]": page})
            results.extend(data.get("data", []))
            if not data.get("links", {}).get("next"):
                break
            page += 1
        return results
    
    async def get_documents(self, org_id: str) -> list[dict]:
        results = []
        page = 1
        while True:
            data = await self._get(
                f"/organizations/{org_id}/relationships/documents", 
                {"page[size]": PAGE_SIZE, "page[number]": page}
            )
            for item in data.get("data", []):
                attrs = item.get("attributes", [])
                results.append({
                        "id": item["id"],
                        "name": attrs.get("name"),
                        "document_folder_id": attrs.get("document-folder-id"),
                        "archived": attrs.get("archived"),
                        "restricted": attrs.get("restricted"),
                        "created_at": attrs.get("created-at"),
                        "updated_at": attrs.get("updated-at"),
                })
            if not data.get("links", {}).get("next"):
                break
            page += 1
        return results
    
    
    async def get_flexible_asset_types(self) -> list[dict]:
        data = await self._get("/flexible_asset_types", {"page[size]": 50})
        return [
            {"id": item["id"], "name": item["attributes"]["name"]}
            for item in data.get("data", [])
        ]

    async def get_flexible_assets(self, org_id: str) -> list[dict]:
        types = await self.get_flexible_asset_types()
        results = []
        for asset_type in types:
            page = 1
            while True:
                data = await self._get(
                    "/flexible_assets",
                    {
                        "filter[organization_id]": org_id,
                        "filter[flexible_asset_type_id]": asset_type["id"],
                        "page[size]": PAGE_SIZE,
                        "page[number]": page,
                    }
                )
                for item in data.get("data", []):
                    attrs = item.get("attributes", {})
                    results.append({
                        "id": item["id"],
                        "name": attrs.get("name"),
                        "flexible_asset_type_id": asset_type["id"],
                        "flexible_asset_type_name": asset_type["name"],
                        "created_at": attrs.get("created-at"),
                        "updated_at": attrs.get("updated-at"),
                    })
                if not data.get("links", {}).get("next"):
                    break
                page += 1
        return results

    
    
    
    async def verify(self) -> dict:
        """Quck check - get page 1 only, return meta."""
        data = await self._get("/organizations", {"page[size]": 1, "page[number]": 1})
        return {"total_organizations": data.get("meta", {}).get("total-count", 0)}
    
    
    

