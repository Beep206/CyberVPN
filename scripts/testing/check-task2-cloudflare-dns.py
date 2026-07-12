from __future__ import annotations

import json
import os
import socket
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API = "https://api.cloudflare.com/client/v4"
ZONE = "cyber-vpn.org"
NAME = "spb-exceptions.cyber-vpn.org"
EXPECTED_IPV4 = "193.233.91.99"
EXPECTED_TTL = 300
EXPECTED_PORTS = (4443, 8444)


def cloudflare_get(path: str, token: str) -> dict[str, object]:
    request = Request(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("success"):
        raise RuntimeError("Cloudflare rejected the read-only DNS query")
    return payload


def main() -> None:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("CLOUDFLARE_API_TOKEN is required")

    zones = cloudflare_get(
        f"/zones?{urlencode({'name': ZONE, 'status': 'active'})}",
        token,
    )["result"]
    if not isinstance(zones, list) or len(zones) != 1:
        raise RuntimeError("Expected exactly one active Cloudflare zone")
    zone_id = zones[0]["id"]
    records = cloudflare_get(
        f"/zones/{zone_id}/dns_records?{urlencode({'name': NAME})}",
        token,
    )["result"]
    if not isinstance(records, list):
        raise RuntimeError("Cloudflare DNS response is not a record list")
    address_records = [
        record for record in records if record.get("type") in {"A", "AAAA"}
    ]
    expected_records = [
        record
        for record in address_records
        if record.get("type") == "A"
        and record.get("content") == EXPECTED_IPV4
        and record.get("ttl") == EXPECTED_TTL
        and record.get("proxied") is False
    ]
    if len(address_records) != 1 or len(expected_records) != 1:
        raise RuntimeError("Task2 Cloudflare A-only record does not match the contract")

    resolved_ipv4 = sorted(
        {
            item[4][0]
            for item in socket.getaddrinfo(
                NAME, 443, socket.AF_INET, socket.SOCK_STREAM
            )
        }
    )
    if resolved_ipv4 != [EXPECTED_IPV4]:
        raise RuntimeError("Public IPv4 DNS does not match the Cloudflare record")
    try:
        resolved_ipv6 = {
            item[4][0]
            for item in socket.getaddrinfo(
                NAME, 443, socket.AF_INET6, socket.SOCK_STREAM
            )
        }
    except socket.gaierror:
        resolved_ipv6 = set()
    if resolved_ipv6:
        raise RuntimeError("Task2 customer alias unexpectedly publishes IPv6")

    for port in EXPECTED_PORTS:
        with socket.create_connection((NAME, port), timeout=5):
            pass
    print("task2_cloudflare_dns=pass records=1 ipv4=1 ipv6=0 ports=2")


if __name__ == "__main__":
    main()
