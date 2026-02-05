"""Tests for security headers middleware (MED-2)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

from src.presentation.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance with mock app."""
        app = AsyncMock()
        return SecurityHeadersMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = MagicMock(spec=Request)
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response with empty headers."""
        response = MagicMock(spec=Response)
        response.headers = {}
        return response

    @pytest.mark.asyncio
    async def test_adds_x_content_type_options(self, middleware, mock_request, mock_response):
        """X-Content-Type-Options header is set to nosniff."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        assert mock_response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_adds_x_frame_options(self, middleware, mock_request, mock_response):
        """X-Frame-Options header is set to DENY."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        assert mock_response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_adds_x_xss_protection(self, middleware, mock_request, mock_response):
        """X-XSS-Protection header is set correctly."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        assert mock_response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_adds_referrer_policy(self, middleware, mock_request, mock_response):
        """Referrer-Policy header is set correctly."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        assert mock_response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_adds_csp_header(self, middleware, mock_request, mock_response):
        """Content-Security-Policy header is set with required directives."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        csp = mock_response.headers["Content-Security-Policy"]

        # Verify key CSP directives are present
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

    @pytest.mark.asyncio
    async def test_adds_permissions_policy(self, middleware, mock_request, mock_response):
        """Permissions-Policy header restricts dangerous features."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        permissions = mock_response.headers["Permissions-Policy"]

        # Verify dangerous features are disabled
        assert "geolocation=()" in permissions
        assert "microphone=()" in permissions
        assert "camera=()" in permissions

    @pytest.mark.asyncio
    async def test_adds_cache_control_if_missing(self, middleware, mock_request, mock_response):
        """Cache-Control header is added when not present."""
        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        assert mock_response.headers["Cache-Control"] == "no-store, max-age=0"

    @pytest.mark.asyncio
    async def test_preserves_existing_cache_control(self, middleware, mock_request, mock_response):
        """Existing Cache-Control header is preserved."""
        mock_response.headers["Cache-Control"] = "public, max-age=3600"

        async def call_next(_):
            return mock_response

        await middleware.dispatch(mock_request, call_next)
        assert mock_response.headers["Cache-Control"] == "public, max-age=3600"

    @pytest.mark.asyncio
    async def test_hsts_in_production(self, middleware, mock_request, mock_response):
        """HSTS header is added when debug is False."""
        with patch("src.presentation.middleware.security_headers.settings") as mock_settings:
            mock_settings.debug = False

            async def call_next(_):
                return mock_response

            await middleware.dispatch(mock_request, call_next)
            assert "Strict-Transport-Security" in mock_response.headers
            assert "max-age=31536000" in mock_response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_no_hsts_in_debug(self, middleware, mock_request, mock_response):
        """HSTS header is NOT added when debug is True."""
        with patch("src.presentation.middleware.security_headers.settings") as mock_settings:
            mock_settings.debug = True

            async def call_next(_):
                return mock_response

            await middleware.dispatch(mock_request, call_next)
            assert "Strict-Transport-Security" not in mock_response.headers
