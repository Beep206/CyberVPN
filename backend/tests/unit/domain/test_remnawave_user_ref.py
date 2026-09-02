from uuid import uuid4

import pytest

from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


@pytest.mark.unit
@pytest.mark.parametrize("invalid_id", [True, False, 0, -1, 1.5, "1"])
def test_remnawave_user_ref_rejects_non_positive_or_non_integer_numeric_identity(invalid_id) -> None:
    with pytest.raises(ValueError, match="positive"):
        RemnawaveUserRef(id=invalid_id)


@pytest.mark.unit
def test_legacy_uuid_is_available_only_through_explicit_rollback_identifier() -> None:
    legacy_uuid = uuid4()
    ref = RemnawaveUserRef(legacy_uuid=legacy_uuid)

    with pytest.raises(ValueError, match="not been reconciled"):
        _ = ref.canonical
    assert ref.rollback_identifier == legacy_uuid
