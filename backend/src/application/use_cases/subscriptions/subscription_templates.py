from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionResponse, StatusMessageResponse


class SubscriptionTemplatesUseCase:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    @staticmethod
    def _dump_validated_model(data) -> dict:
        return data.model_dump(by_alias=True, mode="json")

    async def list_templates(self) -> list[dict]:
        data = await self._client.get_collection_validated(
            "/api/subscription-templates",
            "templates",
            RemnawaveSubscriptionResponse,
        )
        return [self._dump_validated_model(item) for item in data]

    async def get_template(self, uuid: str) -> dict:
        data = await self._client.get_validated(f"/api/subscription-templates/{uuid}", RemnawaveSubscriptionResponse)
        return self._dump_validated_model(data)

    async def create_template(self, name: str, template_type: str, content: str) -> dict:
        data = await self._client.post_validated(
            "/api/subscription-templates",
            RemnawaveSubscriptionResponse,
            json={"name": name, "templateType": template_type, "content": content},
        )
        return self._dump_validated_model(data)

    async def update_template(self, uuid: str, **kwargs) -> dict:
        data = await self._client.put_validated(
            f"/api/subscription-templates/{uuid}",
            RemnawaveSubscriptionResponse,
            json=kwargs,
        )
        return self._dump_validated_model(data)

    async def delete_template(self, uuid: str) -> None:
        await self._client.delete_validated(f"/api/subscription-templates/{uuid}", StatusMessageResponse)
