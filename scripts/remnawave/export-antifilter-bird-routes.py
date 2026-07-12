#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import queue
import re
import shutil
import subprocess  # noqa: S404 - birdc is invoked with fixed argv and shell disabled.
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Literal

SOURCE_SCHEMA_VERSION = 1
SOURCE_TYPE = "bgp-canonical-cidr"
SOURCE_PROVIDER = "antifilter.network"
DEFAULT_COLLECTOR = "cybervpn-antifilter-bgp-bird2"
REQUIRED_COMMUNITIES: tuple[str, ...] = (
    "65444:100",
    "65444:700",
    "65444:710",
    "65444:720",
    "65444:730",
    "65444:740",
    "65444:750",
    "65444:760",
    "65444:770",
    "65444:780",
    "65444:790",
    "65444:800",
    "65444:65444",
)
FORBIDDEN_NETWORKS: tuple[Network, ...] = tuple(
    ipaddress.ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/3",
        "::/127",
        "2001:db8::/32",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    )
)
MAX_SOURCE_VERSION_LENGTH = 120
SAFE_SOURCE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$")
ROUTE_LINE = re.compile(r"^\s*(?P<prefix>[0-9A-Fa-f:.]+/\d{1,3})(?:\s|$)")
CONTINUATION_LINE = re.compile(
    r"^\s+(?:"
    r"via\b|dev\b|from\b|unreachable\b|blackhole\b|"
    r"BGP\.|Type:|Preference:|Source:|IGP metric:"
    r")"
)
HEADER_LINE_PREFIXES = (
    "BIRD ",
    "Table ",
    "Access restricted",
    "Router ID is ",
    "Route change stats:",
)

Network = ipaddress.IPv4Network | ipaddress.IPv6Network
Ipv6PolicyMode = Literal["enabled", "disabled", "fallback_block"]


class ExportError(ValueError):
    """Safe operator-facing rejection of untrusted BIRD state or output."""


@dataclass(frozen=True)
class ExportOptions:
    birdc: Path
    socket: Path
    output_root: Path
    collector: str
    protocol_ipv4: str
    table_ipv4: str
    protocol_ipv6: str
    table_ipv6: str
    ipv6_policy: Ipv6PolicyMode
    ipv6_policy_reason: str
    generated_at: datetime
    source_version: str
    timeout_seconds: int
    max_output_bytes: int
    max_lines_per_community: int


class BirdClient:
    def __init__(
        self, birdc: Path, socket: Path, timeout_seconds: int, max_output_bytes: int
    ) -> None:
        self._birdc = birdc
        self._socket = socket
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes

    def run(self, command: str) -> str:
        if "\x00" in command or "\n" in command or "\r" in command:
            raise ExportError("refusing malformed birdc command")
        argv = [str(self._birdc), "-s", str(self._socket), command]
        try:
            process = subprocess.Popen(  # noqa: S603 - argv list is fixed, shell is not used.
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ExportError(f"birdc executable is missing: {self._birdc}") from exc
        except OSError as exc:
            raise ExportError(f"cannot execute birdc: {exc}") from exc

        stdout, stderr = _read_bounded_process_output(
            process,
            timeout_seconds=self._timeout_seconds,
            max_output_bytes=self._max_output_bytes,
        )
        try:
            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ExportError("birdc output must be UTF-8") from exc
        if process.returncode != 0:
            raise ExportError(
                f"birdc command failed with exit code {process.returncode}: {stderr_text.strip()}"
            )
        if stderr_text.strip():
            raise ExportError(
                f"birdc wrote stderr for a required command: {stderr_text.strip()}"
            )
        return stdout_text

    def assert_protocol_ready(
        self, protocol: str, family: Literal["ipv4", "ipv6"]
    ) -> None:
        output = self.run(f"show protocols all {protocol}")
        if not re.search(r"\bBGP state:\s+Established\b", output):
            raise ExportError(f"BIRD protocol {protocol} is not Established")
        if not _channel_is_up(output, family):
            raise ExportError(f"BIRD protocol {protocol} channel {family} is not UP")

    def query_routes(self, table: str, community: str) -> str:
        asn, value = _split_community(community)
        return self.run(
            f"show route table {table} where ({asn},{value}) ~ bgp_community"
        )


def _channel_is_up(output: str, family: Literal["ipv4", "ipv6"]) -> bool:
    in_channel = False
    channel_pattern = re.compile(rf"^\s*Channel\s+{re.escape(family)}\b")
    other_channel_pattern = re.compile(r"^\s*Channel\s+\S+")
    for line in output.splitlines():
        if channel_pattern.search(line):
            in_channel = True
            continue
        if in_channel and re.search(r"^\s*State:\s+UP\b", line):
            return True
        if in_channel and other_channel_pattern.search(line):
            return False
    return False


def _split_community(community: str) -> tuple[int, int]:
    left, separator, right = community.partition(":")
    if separator != ":":
        raise ExportError(f"invalid BGP community: {community!r}")
    try:
        asn = int(left)
        value = int(right)
    except ValueError as exc:
        raise ExportError(f"invalid BGP community: {community!r}") from exc
    if not (0 <= asn <= 65535 and 0 <= value <= 65535):
        raise ExportError(f"BGP community is outside standard range: {community!r}")
    return asn, value


StreamEvent = tuple[str, bytes | BaseException | None]


def _read_pipe(name: str, pipe: BinaryIO, events: queue.Queue[StreamEvent]) -> None:
    try:
        while True:
            chunk = pipe.read(65_536)
            if not chunk:
                break
            events.put((name, chunk))
    except (
        BaseException
    ) as exc:  # pragma: no cover - defensive cross-platform pipe failure path.
        events.put((name, exc))
    finally:
        events.put((name, None))


def _read_bounded_process_output(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: int,
    max_output_bytes: int,
) -> tuple[bytes, bytes]:
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise ExportError("birdc pipes were not captured")

    events: queue.Queue[StreamEvent] = queue.Queue()
    threads = (
        threading.Thread(
            target=_read_pipe, args=("stdout", process.stdout, events), daemon=True
        ),
        threading.Thread(
            target=_read_pipe, args=("stderr", process.stderr, events), daemon=True
        ),
    )
    for thread in threads:
        thread.start()

    chunks: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    closed = 0
    total = 0
    deadline = time.monotonic() + timeout_seconds
    while closed < 2:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            process.kill()
            _join_reader_threads(threads)
            raise ExportError(
                f"birdc command timed out after {timeout_seconds} seconds"
            )
        try:
            name, payload = events.get(timeout=min(remaining, 0.1))
        except queue.Empty:
            continue
        if payload is None:
            closed += 1
            continue
        if isinstance(payload, BaseException):
            process.kill()
            _join_reader_threads(threads)
            raise ExportError(f"cannot read birdc {name}: {payload}") from payload
        total += len(payload)
        if total > max_output_bytes:
            process.kill()
            _join_reader_threads(threads)
            raise ExportError(f"birdc output exceeds {max_output_bytes} bytes")
        chunks[name].append(payload)

    try:
        process.wait(timeout=max(deadline - time.monotonic(), 0.001))
    except subprocess.TimeoutExpired as exc:
        process.kill()
        _join_reader_threads(threads)
        raise ExportError(
            f"birdc command timed out after {timeout_seconds} seconds"
        ) from exc
    _join_reader_threads(threads)
    return b"".join(chunks["stdout"]), b"".join(chunks["stderr"])


def _join_reader_threads(threads: tuple[threading.Thread, threading.Thread]) -> None:
    for thread in threads:
        thread.join(timeout=1)


def _network_key(network: Network) -> tuple[int, int, int]:
    return network.version, int(network.network_address), network.prefixlen


def parse_route_output(
    output: str, *, family: int, community: str, max_lines: int
) -> list[Network]:
    lines = output.splitlines()
    if len(lines) > max_lines:
        raise ExportError(f"community {community} output exceeds {max_lines} lines")
    networks: set[Network] = set()
    for index, line in enumerate(lines, start=1):
        if not line:
            continue
        if line.startswith(HEADER_LINE_PREFIXES):
            continue
        if line[:1].isspace() and not ROUTE_LINE.match(line):
            if not CONTINUATION_LINE.match(line):
                raise ExportError(
                    f"malformed BIRD route output for {community} at line {index}"
                )
            continue
        match = ROUTE_LINE.match(line)
        if match is None:
            raise ExportError(
                f"malformed BIRD route output for {community} at line {index}"
            )
        try:
            network = ipaddress.ip_network(match.group("prefix"), strict=True)
        except ValueError as exc:
            raise ExportError(
                f"invalid CIDR prefix for {community} at line {index}"
            ) from exc
        if network.version != family:
            raise ExportError(
                f"address family mismatch for {community} at line {index}"
            )
        if any(
            network.overlaps(forbidden)
            for forbidden in FORBIDDEN_NETWORKS
            if forbidden.version == family
        ):
            raise ExportError(
                f"forbidden or unsafe CIDR prefix for {community} at line {index}"
            )
        networks.add(network)
    if not networks:
        raise ExportError(f"required community {community} has no IPv{family} routes")
    return sorted(networks, key=_network_key)


def export_candidate(options: ExportOptions, client: BirdClient | None = None) -> Path:
    _validate_options(options)
    bird = client or BirdClient(
        options.birdc,
        options.socket,
        options.timeout_seconds,
        options.max_output_bytes,
    )
    families: list[tuple[int, str, str, Literal["ipv4", "ipv6"]]] = [
        (4, options.table_ipv4, options.protocol_ipv4, "ipv4")
    ]
    if options.ipv6_policy == "enabled":
        families.append((6, options.table_ipv6, options.protocol_ipv6, "ipv6"))

    for _, _, protocol, family_name in families:
        bird.assert_protocol_ready(protocol, family_name)

    payloads: dict[str, bytes] = {}
    source_files: list[dict[str, Any]] = []
    for family, table, _, _ in families:
        for community in REQUIRED_COMMUNITIES:
            routes = parse_route_output(
                bird.query_routes(table, community),
                family=family,
                community=community,
                max_lines=options.max_lines_per_community,
            )
            relative = f"{community.replace(':', '_')}.ipv{family}.cidr"
            content = _cidr_bytes(routes)
            payloads[relative] = content
            source_files.append(
                {
                    "community": community,
                    "family": family,
                    "path": relative,
                    "sha256": _sha256_bytes(content),
                }
            )

    source = {
        "schemaVersion": SOURCE_SCHEMA_VERSION,
        "source": {
            "type": SOURCE_TYPE,
            "provider": SOURCE_PROVIDER,
            "collector": options.collector,
            "generatedAt": _format_utc_timestamp(options.generated_at),
            "sourceVersion": options.source_version,
        },
        "files": source_files,
        "ipv6Policy": {
            "mode": options.ipv6_policy,
            "reason": options.ipv6_policy_reason.strip(),
        },
    }
    payloads["source.json"] = _canonical_json_bytes(source)
    return _atomic_write_candidate(
        options.output_root, options.source_version, payloads
    )


def _validate_options(options: ExportOptions) -> None:
    if (
        options.generated_at.tzinfo is None
        or options.generated_at.utcoffset() != UTC.utcoffset(options.generated_at)
    ):
        raise ExportError("generated_at must be a UTC-aware timestamp")
    if (
        not SAFE_SOURCE_VERSION.fullmatch(options.source_version)
        or len(options.source_version) > MAX_SOURCE_VERSION_LENGTH
    ):
        raise ExportError("sourceVersion must be a safe 1-120 character path segment")
    if not options.collector.strip() or len(options.collector) > 200:
        raise ExportError("collector must contain 1-200 characters")
    if options.ipv6_policy not in {"enabled", "disabled", "fallback_block"}:
        raise ExportError("invalid IPv6 policy mode")
    if not options.ipv6_policy_reason.strip() or len(options.ipv6_policy_reason) > 500:
        raise ExportError("IPv6 policy reason must contain 1-500 characters")
    for field_name in ("protocol_ipv4", "table_ipv4", "protocol_ipv6", "table_ipv6"):
        value = getattr(options, field_name)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", value):
            raise ExportError(f"{field_name} is not a safe BIRD identifier")
    if options.timeout_seconds < 1 or options.timeout_seconds > 120:
        raise ExportError("timeout must be between 1 and 120 seconds")
    if options.max_output_bytes < 1024 or options.max_output_bytes > 268_435_456:
        raise ExportError("max output bytes must be between 1024 and 268435456")
    if (
        options.max_lines_per_community < 1
        or options.max_lines_per_community > 2_000_000
    ):
        raise ExportError("max lines per community must be between 1 and 2000000")


def _cidr_bytes(networks: list[Network]) -> bytes:
    return (
        "\n".join(str(network) for network in sorted(networks, key=_network_key)) + "\n"
    ).encode("ascii")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ExportError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must be RFC3339 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise argparse.ArgumentTypeError("timestamp must be UTC")
    return parsed.astimezone(UTC)


def _safe_relative_path(relative: str) -> PurePosixPath:
    if not relative or "\\" in relative:
        raise ExportError(f"unsafe relative path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ExportError(f"unsafe relative path: {relative!r}")
    return pure


def _ensure_no_symlink_ancestry(path: Path) -> None:
    resolved = path.absolute()
    for candidate in (resolved, *resolved.parents):
        if candidate.exists() and candidate.is_symlink():
            raise ExportError(f"refusing symlinked output path: {candidate}")


def _atomic_write_candidate(
    output_root: Path, source_version: str, files: dict[str, bytes]
) -> Path:
    if not output_root.is_absolute():
        raise ExportError("output root must be an absolute path")
    _ensure_no_symlink_ancestry(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    _ensure_no_symlink_ancestry(output_root)
    _chmod_best_effort(output_root, 0o750)
    destination = output_root / source_version
    if destination.exists() or destination.is_symlink():
        raise ExportError(f"candidate already exists: {destination}")
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{source_version}.tmp-", dir=output_root)
    )
    try:
        _chmod_best_effort(temporary, 0o750)
        for relative, content in sorted(files.items()):
            pure = _safe_relative_path(relative)
            target = temporary.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            _chmod_best_effort(target.parent, 0o750)
            with target.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            _chmod_best_effort(target, 0o640)
        _fsync_directory_tree(temporary)
        os.replace(temporary, destination)
        _fsync_directory(output_root)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination / "source.json"


def _chmod_best_effort(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        if os.name != "nt":
            raise


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory_tree(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        _fsync_directory(Path(directory))


def _default_source_version(generated_at: datetime) -> str:
    return "antifilter-bgp-" + generated_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export canonical Antifilter CIDR source files from BIRD2 BGP tables"
    )
    parser.add_argument("--birdc", required=True, type=Path)
    parser.add_argument("--socket", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--collector", default=DEFAULT_COLLECTOR)
    parser.add_argument("--protocol-ipv4", default="antifilter_v4")
    parser.add_argument("--table-ipv4", default="antifilter4")
    parser.add_argument("--protocol-ipv6", default="antifilter_v6")
    parser.add_argument("--table-ipv6", default="antifilter6")
    parser.add_argument(
        "--ipv6-policy",
        choices=("enabled", "disabled", "fallback_block"),
        default="disabled",
    )
    parser.add_argument("--ipv6-policy-reason", required=True)
    parser.add_argument("--generated-at", type=_parse_utc_timestamp)
    parser.add_argument("--source-version")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-output-bytes", type=int, default=67_108_864)
    parser.add_argument("--max-lines-per-community", type=int, default=1_000_000)
    return parser


def _options_from_args(args: argparse.Namespace) -> ExportOptions:
    generated_at = args.generated_at or datetime.now(UTC).replace(microsecond=0)
    source_version = args.source_version or _default_source_version(generated_at)
    return ExportOptions(
        birdc=args.birdc,
        socket=args.socket,
        output_root=args.output_root,
        collector=args.collector,
        protocol_ipv4=args.protocol_ipv4,
        table_ipv4=args.table_ipv4,
        protocol_ipv6=args.protocol_ipv6,
        table_ipv6=args.table_ipv6,
        ipv6_policy=args.ipv6_policy,
        ipv6_policy_reason=args.ipv6_policy_reason,
        generated_at=generated_at,
        source_version=source_version,
        timeout_seconds=args.timeout,
        max_output_bytes=args.max_output_bytes,
        max_lines_per_community=args.max_lines_per_community,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        source_path = export_candidate(_options_from_args(args))
    except ExportError as exc:
        print(
            json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "status": "collected",
                "sourcePath": str(source_path),
                "sourceVersion": source_path.parent.name,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
