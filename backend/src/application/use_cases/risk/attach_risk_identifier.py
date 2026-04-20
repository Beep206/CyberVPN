from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import RiskIdentifierType
from src.infrastructure.database.models.risk_identifier_model import RiskIdentifierModel
from src.infrastructure.database.models.risk_link_model import RiskLinkModel
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository

from ._helpers import (
    build_value_preview,
    canonical_subject_pair,
    derive_link_type,
    hash_identifier_value,
    normalize_identifier_value,
)


class AttachRiskIdentifierUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)

    async def execute(
        self,
        *,
        risk_subject_id: UUID,
        identifier_type: RiskIdentifierType | str,
        value: str,
        is_verified: bool = False,
        source: str,
    ) -> tuple[RiskIdentifierModel, list[RiskLinkModel]]:
        subject = await self._risk_repo.get_subject_by_id(risk_subject_id)
        if subject is None:
            raise ValueError("Risk subject not found")

        normalized_identifier_type = RiskIdentifierType(identifier_type)
        normalized_value = normalize_identifier_value(identifier_type=normalized_identifier_type, value=value)
        value_hash = hash_identifier_value(normalized_value)

        existing_identifiers = await self._risk_repo.list_identifiers_for_subject(risk_subject_id)
        for existing_identifier in existing_identifiers:
            if (
                existing_identifier.identifier_type == normalized_identifier_type.value
                and existing_identifier.value_hash == value_hash
            ):
                return existing_identifier, []

        identifier = RiskIdentifierModel(
            risk_subject_id=risk_subject_id,
            identifier_type=normalized_identifier_type.value,
            value_hash=value_hash,
            value_preview=build_value_preview(identifier_type=normalized_identifier_type, value=normalized_value),
            is_verified=is_verified,
            source=source.strip(),
        )
        created_identifier = await self._risk_repo.create_identifier(identifier)

        created_links: list[RiskLinkModel] = []
        matching_identifiers = await self._risk_repo.list_matching_identifiers(
            identifier_type=normalized_identifier_type.value,
            value_hash=value_hash,
        )
        for matching_identifier in matching_identifiers:
            if matching_identifier.risk_subject_id == risk_subject_id:
                continue

            left_subject_id, right_subject_id = canonical_subject_pair(
                risk_subject_id,
                matching_identifier.risk_subject_id,
            )
            existing_link = await self._risk_repo.get_link_between_subjects(
                left_subject_id=left_subject_id,
                right_subject_id=right_subject_id,
                identifier_type=normalized_identifier_type.value,
            )
            if existing_link is not None:
                continue

            evidence: dict[str, Any] = {
                "source": source.strip(),
                "value_preview": created_identifier.value_preview,
                "matched_identifier_subject_id": str(matching_identifier.risk_subject_id),
            }
            created_links.append(
                await self._risk_repo.create_link(
                    RiskLinkModel(
                        left_subject_id=left_subject_id,
                        right_subject_id=right_subject_id,
                        link_type=derive_link_type(normalized_identifier_type).value,
                        identifier_type=normalized_identifier_type.value,
                        source_identifier_id=created_identifier.id,
                        status="active",
                        evidence=evidence,
                    )
                )
            )

        return created_identifier, created_links

