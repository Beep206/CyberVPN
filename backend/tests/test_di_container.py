"""Tests for the DI container and override mechanism (ARCH-01c)."""

from src.application.services.auth_service import AuthService
from src.infrastructure.di.container import Container, container
from src.infrastructure.di.overrides import override_dependency


def test_container_returns_default_auth_service():
    factory = container.get("auth_service")
    service = factory()
    assert isinstance(service, AuthService)


def test_container_override_replaces_factory():
    class FakeAuthService:
        pass

    container.override("auth_service", lambda: FakeAuthService())
    try:
        factory = container.get("auth_service")
        result = factory()
        assert isinstance(result, FakeAuthService)
    finally:
        container.reset("auth_service")

    # After reset, should return default
    factory = container.get("auth_service")
    assert isinstance(factory(), AuthService)


def test_override_dependency_context_manager():
    class MockAuthService:
        pass

    with override_dependency("auth_service", lambda: MockAuthService()):
        result = container.get("auth_service")()
        assert isinstance(result, MockAuthService)

    # After context exit, default is restored
    result = container.get("auth_service")()
    assert isinstance(result, AuthService)


def test_container_reset_all():
    container.override("auth_service", lambda: "fake")
    container.reset()
    factory = container.get("auth_service")
    assert isinstance(factory(), AuthService)


def test_new_container_is_independent():
    c = Container()
    factory = c.get("auth_service")
    assert isinstance(factory(), AuthService)
