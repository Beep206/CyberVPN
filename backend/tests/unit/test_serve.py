"""Unit tests for the process bootstrap in src.serve."""

from unittest.mock import patch

from src import serve


class TestServeRuntimeConfig:
    def test_build_api_server_uses_runtime_settings(self) -> None:
        with patch.multiple(
            serve.settings,
            api_host="0.0.0.0",
            api_port=18000,
            log_level="WARNING",
            uvicorn_access_log=False,
            uvicorn_server_header=False,
            uvicorn_date_header=True,
            uvicorn_backlog=4096,
            uvicorn_timeout_keep_alive=12,
            uvicorn_timeout_graceful_shutdown=45,
            uvicorn_limit_concurrency=250,
            uvicorn_limit_max_requests=5000,
            trust_proxy_headers=False,
            trusted_proxy_ips=[],
        ):
            server = serve._build_api_server()

        config = server.config
        assert config.host == "0.0.0.0"
        assert config.port == 18000
        assert config.log_level == "warning"
        assert config.access_log is False
        assert config.proxy_headers is False
        assert config.forwarded_allow_ips == "127.0.0.1"
        assert config.server_header is False
        assert config.date_header is True
        assert config.backlog == 4096
        assert config.timeout_keep_alive == 12
        assert config.timeout_graceful_shutdown == 45
        assert config.limit_concurrency == 250
        assert config.limit_max_requests == 5000

    def test_forwarded_allow_ips_uses_trusted_proxy_list(self) -> None:
        with patch.multiple(
            serve.settings,
            trust_proxy_headers=True,
            trusted_proxy_ips=["10.0.0.10", "10.0.0.11"],
        ):
            assert serve._forwarded_allow_ips() == "10.0.0.10,10.0.0.11"

    def test_forwarded_allow_ips_defaults_to_loopback_when_proxy_trust_enabled_without_allowlist(self) -> None:
        with patch.multiple(
            serve.settings,
            trust_proxy_headers=True,
            trusted_proxy_ips=[],
        ):
            assert serve._forwarded_allow_ips() == "127.0.0.1"
