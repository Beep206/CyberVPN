from src.infrastructure.remnawave.client import RemnawaveClient


class SubscriptionTemplatesUseCase:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def list_templates(self) -> list[dict]:
        data = await self._client.get("/api/subscription/templates")
        return data if isinstance(data, list) else data.get("templates", [])

    async def get_template(self, uuid: str) -> dict:
        return await self._client.get(f"/api/subscription/templates/{uuid}")

    async def create_template(self, name: str, template_type: str, content: str) -> dict:
        return await self._client.post(
            "/api/subscription/templates",
            json={"name": name, "templateType": template_type, "content": content},
        )

    async def update_template(self, uuid: str, **kwargs) -> dict:
        return await self._client.put(f"/api/subscription/templates/{uuid}", json=kwargs)

    async def delete_template(self, uuid: str) -> None:
        await self._client.delete(f"/api/subscription/templates/{uuid}")
