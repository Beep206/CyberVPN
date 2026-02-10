"""Security tests for Remnawave proxy response validation (HIGH-4).

Tests that:
1. Valid responses pass validation
2. Invalid responses return 502 Bad Gateway
3. Unexpected fields are stripped
4. Validation failures are logged
"""

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from src.infrastructure.remnawave.response_validator import RemnawaveResponseValidator


class SampleResponse(BaseModel):
    """Sample response schema for testing."""

    id: str
    name: str
    status: str


class TestResponseValidation:
    """Test response validation."""

    def setup_method(self):
        """Create validator for each test."""
        self.validator = RemnawaveResponseValidator()

    def test_valid_response_passes(self):
        """Valid response data passes validation."""
        data = {
            "id": "123",
            "name": "test-host",
            "status": "online",
        }

        result = self.validator.validate_single(data, SampleResponse, "GET /test")

        assert result.id == "123"
        assert result.name == "test-host"
        assert result.status == "online"

    def test_extra_fields_stripped(self):
        """Unexpected fields are stripped from response."""
        data = {
            "id": "123",
            "name": "test-host",
            "status": "online",
            "malicious_field": "<script>alert('xss')</script>",
            "secret_key": "should_not_appear",
        }

        result = self.validator.validate_single(data, SampleResponse, "GET /test")

        # Result should only have expected fields
        assert result.id == "123"
        assert not hasattr(result, "malicious_field")
        assert not hasattr(result, "secret_key")

    def test_invalid_type_raises_502(self):
        """Invalid field type raises 502 Bad Gateway."""
        data = {
            "id": 123,  # Should be string
            "name": "test-host",
            "status": "online",
        }

        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_single(data, SampleResponse, "GET /test")

        assert exc_info.value.status_code == 502
        assert "invalid response" in exc_info.value.detail.lower()

    def test_missing_required_field_raises_502(self):
        """Missing required field raises 502 Bad Gateway."""
        data = {
            "id": "123",
            # Missing 'name' and 'status'
        }

        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_single(data, SampleResponse, "GET /test")

        assert exc_info.value.status_code == 502


class TestListValidation:
    """Test list response validation."""

    def setup_method(self):
        """Create validator for each test."""
        self.validator = RemnawaveResponseValidator()

    def test_valid_list_passes(self):
        """Valid list response passes validation."""
        data = [
            {"id": "1", "name": "host-1", "status": "online"},
            {"id": "2", "name": "host-2", "status": "offline"},
        ]

        result = self.validator.validate_list(data, SampleResponse, "GET /test")

        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"

    def test_non_list_raises_502(self):
        """Non-list response raises 502 Bad Gateway."""
        data = {"id": "123", "name": "test", "status": "online"}  # Should be list

        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_list(data, SampleResponse, "GET /test")

        assert exc_info.value.status_code == 502
        assert "invalid response format" in exc_info.value.detail.lower()

    def test_invalid_item_in_list_raises_502(self):
        """Invalid item in list raises 502 Bad Gateway."""
        data = [
            {"id": "1", "name": "host-1", "status": "online"},
            {"id": 2},  # Invalid - missing fields and wrong type
        ]

        with pytest.raises(HTTPException) as exc_info:
            self.validator.validate_list(data, SampleResponse, "GET /test")

        assert exc_info.value.status_code == 502


class TestSecurityProperties:
    """Test security properties of validation."""

    def test_no_raw_error_exposed(self):
        """Validation errors don't expose internal details to client."""
        validator = RemnawaveResponseValidator()
        data = {"bad": "data"}

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_single(data, SampleResponse, "GET /test")

        # Error message should be generic, not expose schema details
        detail = exc_info.value.detail.lower()
        assert "pydantic" not in detail
        assert "validation" not in detail
        assert "field" not in detail

    def test_upstream_mentioned_in_error(self):
        """Error indicates upstream service issue."""
        validator = RemnawaveResponseValidator()
        data = {"bad": "data"}

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_single(data, SampleResponse, "GET /test")

        assert "upstream" in exc_info.value.detail.lower()
