from __future__ import annotations

from src.infrastructure.remnawave.contracts import RemnawaveCursorPage


def test_remnawave_2_8_cursor_page_uses_response_items_and_next_cursor_alias() -> None:
    page = RemnawaveCursorPage.model_validate(
        {
            "response": [{"uuid": "user-1"}, {"uuid": "user-2"}],
            "nextCursor": "cursor-2",
            "hasNextPage": True,
            "total": 100,
        }
    )

    assert page.items == [{"uuid": "user-1"}, {"uuid": "user-2"}]
    assert page.next_cursor == "cursor-2"
    assert page.has_next_page is True
    assert page.total == 100


def test_remnawave_2_8_cursor_page_accepts_alternate_users_and_has_more_aliases() -> None:
    page = RemnawaveCursorPage.model_validate(
        {
            "users": [{"uuid": "user-3"}],
            "cursor": "cursor-3",
            "hasMore": False,
        }
    )

    assert page.items == [{"uuid": "user-3"}]
    assert page.next_cursor == "cursor-3"
    assert page.has_next_page is False
