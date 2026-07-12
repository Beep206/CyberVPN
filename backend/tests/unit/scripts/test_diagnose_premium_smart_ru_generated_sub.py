from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "scripts" / "testing" / "diagnose-premium-smart-ru-generated-sub.py"
SPEC = importlib.util.spec_from_file_location("diagnose_premium_smart_ru_generated_sub", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _raw_proxy(name: str, **overrides: Any) -> dict[str, Any]:
    proxy = {
        "name": name,
        "type": "vless",
        "server": "de-3.cyber-vpn.org",
        "port": 443,
        "network": "raw",
        "tls": True,
        "flow": "xtls-rprx-vision",
        "servername": "www.microsoft.com",
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "reality-opts": {
            "public-key": "RealityPublicKeyMaterialShouldNeverPrint",
            "short-id": "a1b2c3d4",
        },
    }
    proxy.update(overrides)
    return proxy


def _xhttp_proxy(name: str, **overrides: Any) -> dict[str, Any]:
    proxy = {
        "name": name,
        "type": "vless",
        "server": "de-3.cyber-vpn.org",
        "port": 8443,
        "network": "xhttp",
        "tls": True,
        "servername": "www.microsoft.com",
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "reality-opts": {
            "public-key": "RealityPublicKeyMaterialShouldNeverPrint",
            "short-id": "a1b2c3d4",
        },
    }
    proxy.update(overrides)
    return proxy


def _valid_proxies() -> list[dict[str, Any]]:
    servers = (
        "de-3.cyber-vpn.org",
        "nl-4.cyber-vpn.org",
        "ru-msk-3.cyber-vpn.org",
        "ru-spb-3.cyber-vpn.org",
    )
    return [
        *[_raw_proxy(f"raw-{index}", server=server) for index, server in enumerate(servers, start=1)],
        *[_xhttp_proxy(f"xhttp-{index}", server=server) for index, server in enumerate(servers, start=1)],
    ]


def _write_config(tmp_path: Path, proxies: Any) -> Path:
    path = tmp_path / "generated.yaml"
    path.write_text(yaml.safe_dump({"proxies": proxies}, sort_keys=False), encoding="utf-8")
    return path


def _run_args(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = MODULE.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _run(path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, list[dict[str, Any]], str, str]:
    code = MODULE.main([str(path)])
    captured = capsys.readouterr()
    json_lines = [json.loads(line) for line in captured.out.splitlines()]
    return code, json_lines, captured.out, captured.err


def test_script_path_targets_root_testing_script() -> None:
    assert SCRIPT_PATH.relative_to(REPO_ROOT).parts == (
        "scripts",
        "testing",
        "diagnose-premium-smart-ru-generated-sub.py",
    )


@pytest.mark.parametrize("argv", [[], ["one.yaml", "two.yaml"]])
def test_cli_accepts_exactly_one_yaml_path(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    code, stdout, stderr = _run_args(argv, capsys)

    assert code == MODULE.INPUT_ERROR_EXIT
    assert stdout == ""
    assert stderr == "usage: diagnose-premium-smart-ru-generated-sub.py <generated.yaml>\n"


def test_missing_or_url_like_path_returns_safe_error(capsys: pytest.CaptureFixture[str]) -> None:
    secret_url = "vless://123e4567-e89b-12d3-a456-426614174000@example.invalid?pbk=secret-public-key"

    code, stdout, stderr = _run_args([secret_url], capsys)

    assert code == MODULE.INPUT_ERROR_EXIT
    assert stdout == ""
    assert stderr == "error: cannot read YAML file\n"
    assert secret_url not in stderr
    assert "123e4567-e89b-12d3-a456-426614174000" not in stderr


def test_valid_four_raw_and_four_xhttp_returns_zero_and_safe_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, lines, stdout, stderr = _run(_write_config(tmp_path, _valid_proxies()), capsys)

    assert code == 0
    assert stderr == ""
    assert len(lines) == 9
    assert all(set(line) == MODULE.SAFE_PROXY_FIELDS for line in lines[:-1])
    assert lines[-1] == {
        "invalid_raw_tcp": [],
        "invalid_xhttp": [],
        "raw_location_matrix_valid": True,
        "xhttp_location_matrix_valid": True,
        "vless_reality_raw_tcp_count": 4,
        "vless_reality_xhttp_count": 4,
    }
    assert "123e4567-e89b-12d3-a456-426614174000" not in stdout
    assert "RealityPublicKeyMaterialShouldNeverPrint" not in stdout
    assert "a1b2c3d4" not in stdout


@pytest.mark.parametrize(
    ("profile_index", "expected_code"),
    [(3, MODULE.RAW_LOCATION_MATRIX_EXIT), (7, MODULE.XHTTP_LOCATION_MATRIX_EXIT)],
)
def test_duplicate_compensated_location_matrix_is_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    profile_index: int,
    expected_code: int,
) -> None:
    proxies = _valid_proxies()
    proxies[profile_index]["server"] = "de-3.cyber-vpn.org"

    code, lines, _stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == expected_code
    assert stderr == ""
    matrix_key = "raw_location_matrix_valid" if profile_index < 4 else "xhttp_location_matrix_valid"
    assert lines[-1][matrix_key] is False


@pytest.mark.parametrize(
    ("proxies", "expected_code", "expected_summary"),
    [
        (
            _valid_proxies()[4:],
            MODULE.RAW_COUNT_EXIT,
            {"vless_reality_raw_tcp_count": 0, "vless_reality_xhttp_count": 4},
        ),
        (
            [*_valid_proxies()[:3], *_valid_proxies()[4:]],
            MODULE.RAW_COUNT_EXIT,
            {"vless_reality_raw_tcp_count": 3, "vless_reality_xhttp_count": 4},
        ),
        (
            [*_valid_proxies(), _raw_proxy("raw-extra")],
            MODULE.RAW_COUNT_EXIT,
            {"vless_reality_raw_tcp_count": 5, "vless_reality_xhttp_count": 4},
        ),
        (
            _valid_proxies()[:7],
            MODULE.XHTTP_COUNT_EXIT,
            {"vless_reality_raw_tcp_count": 4, "vless_reality_xhttp_count": 3},
        ),
        (
            [*_valid_proxies(), _xhttp_proxy("xhttp-extra")],
            MODULE.XHTTP_COUNT_EXIT,
            {"vless_reality_raw_tcp_count": 4, "vless_reality_xhttp_count": 5},
        ),
        (
            [*_valid_proxies()[:1], _raw_proxy("bad-raw", flow=None), *_valid_proxies()[2:]],
            MODULE.RAW_INVALID_EXIT,
            {"invalid_raw_tcp": ["bad-raw"]},
        ),
        (
            [*_valid_proxies()[:4], _xhttp_proxy("bad-xhttp", port=443), *_valid_proxies()[5:]],
            MODULE.XHTTP_INVALID_EXIT,
            {"invalid_xhttp": ["bad-xhttp"]},
        ),
    ],
)
def test_count_and_missing_field_failures_return_tz_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    proxies: list[dict[str, Any]],
    expected_code: int,
    expected_summary: dict[str, Any],
) -> None:
    code, lines, _stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == expected_code
    assert stderr == ""
    for key, value in expected_summary.items():
        assert lines[-1][key] == value


@pytest.mark.parametrize(
    "bad_proxy",
    [
        _raw_proxy("bad-raw-port", port=8443),
        _raw_proxy("bad-raw-tls", tls="true"),
        _raw_proxy("bad-raw-server", server=None),
        _raw_proxy("bad-raw-url-server", server="vless://example.invalid/secret"),
        _raw_proxy("bad-raw-sni", servername=None),
        _raw_proxy("bad-raw-public-key", **{"reality-opts": {"short-id": "a1b2c3d4"}}),
        _raw_proxy("bad-raw-short-id", **{"reality-opts": {"public-key": "RealityPublicKeyMaterial"}}),
    ],
)
def test_raw_tcp_missing_or_wrong_required_fields_return_invalid_raw_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    bad_proxy: dict[str, Any],
) -> None:
    proxies = _valid_proxies()
    proxies[0] = bad_proxy

    code, lines, _stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == MODULE.RAW_INVALID_EXIT
    assert stderr == ""
    assert lines[-1]["invalid_raw_tcp"] == [bad_proxy["name"]]


@pytest.mark.parametrize(
    "bad_proxy",
    [
        _xhttp_proxy("bad-xhttp-port", port=443),
        _xhttp_proxy("bad-xhttp-tls", tls="true"),
        _xhttp_proxy("bad-xhttp-server", server=None),
        _xhttp_proxy("bad-xhttp-url-server", server="vless://example.invalid/secret"),
        _xhttp_proxy("bad-xhttp-sni", servername=None),
        _xhttp_proxy("bad-xhttp-public-key", **{"reality-opts": {"short-id": "a1b2c3d4"}}),
        _xhttp_proxy("bad-xhttp-short-id", **{"reality-opts": {"public-key": "RealityPublicKeyMaterial"}}),
    ],
)
def test_xhttp_missing_or_wrong_required_fields_return_invalid_xhttp_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    bad_proxy: dict[str, Any],
) -> None:
    proxies = _valid_proxies()
    proxies[4] = bad_proxy

    code, lines, _stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == MODULE.XHTTP_INVALID_EXIT
    assert stderr == ""
    assert lines[-1]["invalid_xhttp"] == [bad_proxy["name"]]


@pytest.mark.parametrize(
    ("proxies", "expected_code"),
    [
        (
            [*_valid_proxies()[:3], _xhttp_proxy("bad-xhttp", port=443), *_valid_proxies()[5:]],
            MODULE.RAW_COUNT_EXIT,
        ),
        (
            [_raw_proxy("bad-raw", flow=None), *_valid_proxies()[1:7]],
            MODULE.XHTTP_COUNT_EXIT,
        ),
        (
            [_raw_proxy("bad-raw", flow=None), *_valid_proxies()[1:4], _xhttp_proxy("bad-xhttp", port=443)],
            MODULE.XHTTP_COUNT_EXIT,
        ),
        (
            [
                _raw_proxy("bad-raw", flow=None),
                *_valid_proxies()[1:4],
                _xhttp_proxy("bad-xhttp", port=443),
                *_valid_proxies()[5:],
            ],
            MODULE.RAW_INVALID_EXIT,
        ),
    ],
)
def test_exit_code_precedence_matches_tz(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    proxies: list[dict[str, Any]],
    expected_code: int,
) -> None:
    code, _lines, _stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == expected_code
    assert stderr == ""


@pytest.mark.parametrize(
    ("yaml_text", "expected_error"),
    [
        (
            "proxies:\n"
            "  - name: vless://123e4567-e89b-12d3-a456-426614174000@example.invalid\n"
            "    short-id: fedcba9876543210\n"
            "    type: [",
            "error: malformed YAML\n",
        ),
        ("", "error: generated config root is not an object\n"),
        ("- not-an-object\n", "error: generated config root is not an object\n"),
        ("proxies: not-a-list\n", "error: generated config proxies is not a list\n"),
        ("proxies:\n  - not-an-object\n", "error: generated config proxy entry is not an object\n"),
    ],
)
def test_malformed_yaml_root_and_proxy_values_return_stable_safe_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    yaml_text: str,
    expected_error: str,
) -> None:
    path = tmp_path / "generated.yaml"
    path.write_text(yaml_text, encoding="utf-8")

    code, lines, _stdout, stderr = _run(path, capsys)

    assert code == MODULE.INPUT_ERROR_EXIT
    assert lines == []
    assert stderr == expected_error
    if yaml_text:
        assert yaml_text not in stderr
    assert "123e4567-e89b-12d3-a456-426614174000" not in stderr
    assert "fedcba9876543210" not in stderr


def test_non_vless_noise_is_ignored_and_not_printed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_noise = "vless://123e4567-e89b-12d3-a456-426614174000@example.invalid?short-id=fedcba9876543210"
    proxies = [
        {"name": secret_noise, "type": "ss", "server": secret_noise},
        *_valid_proxies(),
    ]

    code, lines, stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == 0
    assert stderr == ""
    assert len(lines) == 9
    assert secret_noise not in stdout


def test_repeated_runs_are_deterministic_and_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_config(tmp_path, _valid_proxies())

    first = _run(path, capsys)
    second = _run(path, capsys)

    assert first == second
    assert sorted(item.name for item in tmp_path.iterdir()) == ["generated.yaml"]


def test_missing_proxy_name_uses_safe_deterministic_placeholder(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad_raw = _raw_proxy("removed-name", flow=None)
    del bad_raw["name"]
    proxies = _valid_proxies()
    proxies[0] = bad_raw

    code, lines, _stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == MODULE.RAW_INVALID_EXIT
    assert stderr == ""
    assert lines[0]["name"] == "<unnamed:0>"
    assert lines[-1]["invalid_raw_tcp"] == ["<unnamed:0>"]


def test_output_redacts_urls_and_secret_shaped_identifiers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_url = "vless://123e4567-e89b-12d3-a456-426614174000@example.invalid?pbk=secret-public-key"
    secret_name = "123e4567-e89b-12d3-a456-426614174000"
    public_key = "PublicKeyMaterialThatMustStayOutOfEvidence"
    short_id = "fedcba9876543210"
    proxies = _valid_proxies()
    proxies[0] = _raw_proxy(
        secret_name,
        server=secret_url,
        **{"reality-opts": {"public-key": public_key, "short-id": short_id}},
    )
    proxies[1] = _raw_proxy(short_id, server=short_id)
    proxies[2] = _raw_proxy(f"DE {public_key}")

    code, lines, stdout, stderr = _run(_write_config(tmp_path, proxies), capsys)

    assert code == MODULE.RAW_INVALID_EXIT
    assert stderr == ""
    assert lines[0]["name"] == "<redacted:0>"
    assert lines[0]["server"] == "[redacted]"
    assert lines[1]["name"] == "<redacted:1>"
    assert lines[1]["server"] == "[redacted]"
    assert lines[2]["name"] == "<redacted:2>"
    assert lines[-1]["invalid_raw_tcp"] == ["<redacted:0>", "<redacted:1>"]
    assert "vless://" not in stdout
    assert "123e4567-e89b-12d3-a456-426614174000" not in stdout
    assert "secret-public-key" not in stdout
    assert public_key not in stdout
    assert short_id not in stdout
