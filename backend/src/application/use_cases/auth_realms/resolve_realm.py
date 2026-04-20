"""Resolve auth realm context for requests and token issuance."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository

AUTH_REALM_HEADER = "X-Auth-Realm"


@dataclass(frozen=True)
class RealmResolution:
    auth_realm: AuthRealmModel
    source: str
    host: str | None = None
    storefront_key: str | None = None

    @property
    def realm_id(self) -> str:
        return str(self.auth_realm.id)

    @property
    def realm_key(self) -> str:
        return self.auth_realm.realm_key

    @property
    def realm_type(self) -> str:
        return self.auth_realm.realm_type

    @property
    def audience(self) -> str:
        return self.auth_realm.audience

    @property
    def cookie_namespace(self) -> str:
        return self.auth_realm.cookie_namespace


class ResolveRealmContextUseCase:
    def __init__(self, repo: AuthRealmRepository) -> None:
        self._repo = repo

    async def execute(self, request: Request, *, realm_type_hint: str | None = None) -> RealmResolution:
        header_key = request.headers.get(AUTH_REALM_HEADER)
        if header_key:
            realm = await self._repo.get_realm_by_key(header_key)
            if realm:
                return RealmResolution(auth_realm=realm, source="header")

        host_header = request.headers.get("X-Forwarded-Host") or request.headers.get("Host")
        if host_header:
            realm = await self._repo.get_realm_by_storefront_host(host_header)
            if realm:
                return RealmResolution(auth_realm=realm, source="host", host=host_header.split(":", 1)[0].lower())

        resolved_realm_type = realm_type_hint or _infer_realm_type_from_request(request)
        realm = await self._repo.get_or_create_default_realm(resolved_realm_type)
        return RealmResolution(auth_realm=realm, source="default")


def _infer_realm_type_from_request(request: Request) -> str:
    path = request.url.path
    if path.startswith("/api/v1/mobile/"):
        return "customer"
    if path.startswith("/api/v1/admin/"):
        return "admin"
    if path.startswith("/api/v1/auth/"):
        return "admin"
    return "customer"
