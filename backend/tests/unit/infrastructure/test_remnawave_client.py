from src.infrastructure.remnawave.client import RemnawaveClient


def test_normalize_base_url_strips_api_suffix():
    assert RemnawaveClient._normalize_base_url("http://localhost:3005/api") == "http://localhost:3005"
    assert RemnawaveClient._normalize_base_url("http://localhost:3005") == "http://localhost:3005"


def test_normalize_path_prefixes_api_once():
    assert RemnawaveClient._normalize_path("/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("/api/system/health") == "/api/system/health"
    assert RemnawaveClient._normalize_path("node-plugins") == "/api/node-plugins"
