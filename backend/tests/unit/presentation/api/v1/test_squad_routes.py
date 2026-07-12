from src.infrastructure.remnawave.contracts import RemnawaveRawSquadResponse
from src.presentation.api.v1.squads.routes import _map_squad


def test_map_squad_preserves_remnawave_alias_response() -> None:
    upstream = RemnawaveRawSquadResponse.model_validate(
        {
            "uuid": "squad-1",
            "name": "Premium Smart RU",
            "info": {"membersCount": 7},
        }
    )

    payload = _map_squad(upstream, "internal").model_dump(by_alias=True)

    assert payload == {
        "uuid": "squad-1",
        "name": "Premium Smart RU",
        "squadType": "internal",
        "maxMembers": None,
        "isActive": True,
        "description": None,
        "memberCount": 7,
    }
