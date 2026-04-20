from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.risk_identifier import RiskIdentifier
from src.domain.entities.risk_link import RiskLink
from src.domain.entities.risk_review import RiskReview
from src.domain.entities.risk_subject import RiskSubject


class RiskSubjectRepository(ABC):
    @abstractmethod
    async def create_subject(self, subject: RiskSubject) -> RiskSubject: ...

    @abstractmethod
    async def get_subject_by_id(self, risk_subject_id: UUID) -> RiskSubject | None: ...

    @abstractmethod
    async def get_subject_by_principal(
        self,
        *,
        principal_class: str,
        principal_subject: str,
        auth_realm_id: UUID | None,
    ) -> RiskSubject | None: ...

    @abstractmethod
    async def create_identifier(self, identifier: RiskIdentifier) -> RiskIdentifier: ...

    @abstractmethod
    async def list_identifiers_for_subject(self, risk_subject_id: UUID) -> list[RiskIdentifier]: ...

    @abstractmethod
    async def list_matching_identifiers(
        self,
        *,
        identifier_type: str,
        value_hash: str,
    ) -> list[RiskIdentifier]: ...

    @abstractmethod
    async def get_link_between_subjects(
        self,
        *,
        left_subject_id: UUID,
        right_subject_id: UUID,
        identifier_type: str,
    ) -> RiskLink | None: ...

    @abstractmethod
    async def create_link(self, link: RiskLink) -> RiskLink: ...

    @abstractmethod
    async def list_links_for_subject(self, risk_subject_id: UUID) -> list[RiskLink]: ...

    @abstractmethod
    async def create_review(self, review: RiskReview) -> RiskReview: ...

    @abstractmethod
    async def list_reviews_for_subject(self, risk_subject_id: UUID) -> list[RiskReview]: ...
