import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DNS_ROOT = REPO_ROOT / "infra" / "terraform" / "live" / "production" / "dns"


def _read(name: str) -> str:
    return (DNS_ROOT / name).read_text(encoding="utf-8")


def test_production_dns_accepts_one_explicit_or_edge_state_source() -> None:
    main = _read("main.tf")
    variables = _read("variables.tf")

    assert re.search(r"node\s+=\s+optional\(string\)", variables)
    assert re.search(r"content\s+=\s+optional\(string\)", variables)
    assert re.search(r'record_class\s+=\s+optional\(string, "edge"\)', variables)
    assert 'contains(["A", "AAAA"], record.type)' in variables
    assert 'contains(["edge", "vpn-node"], record.record_class)' in variables
    assert (
        'each.value.record_class == "vpn-node" ? trimspace(each.value.content)' in main
    )
    assert "count   = length(local.edge_records) > 0 ? 1 : 0" in main
    assert "data.terraform_remote_state.edge[0]" in main


def test_de3_dual_stack_records_are_explicit_and_dns_only() -> None:
    example = _read("terraform.tfvars.example")

    assert example.count('name         = "de-3.cyber-vpn.org"') == 2
    assert 'content      = "138.124.115.206"' in example
    assert 'content      = "2a0b:4140:ba84::2"' in example
    for key, record_type in (("de-3-vpn-ipv4", "A"), ("de-3-vpn-ipv6", "AAAA")):
        record = example.split(f"{key} = {{", 1)[1].split("}", 1)[0]
        assert 'record_class = "vpn-node"' in record
        assert f'type         = "{record_type}"' in record
        assert "proxied      = false" in record
    assert len(re.findall(r"proxied\s*=\s*false", example)) >= 4
    assert re.search(
        r'tags\s*=\s*\["environment:production", "component:vpn-node", "region:de"\]',
        example,
    )


def test_spb_exceptions_dedicated_ipv4_record_is_explicit_and_dns_only() -> None:
    example = _read("terraform.tfvars.example")

    assert example.count('name         = "spb-exceptions.cyber-vpn.org"') == 1
    assert 'content      = "193.233.91.99"' in example
    assert "spb-exceptions-vpn-ipv4" in example
    assert "spb-exceptions-vpn-ipv6" not in example
    record = example.split("spb-exceptions-vpn-ipv4 = {", 1)[1].split("}", 1)[0]
    assert 'record_class = "vpn-node"' in record
    assert 'type         = "A"' in record
    assert "ttl          = 300" in record
    assert "proxied      = false" in record


def test_existing_records_require_import_before_apply() -> None:
    readme = _read("README.md")
    compact_readme = " ".join(readme.split())

    assert "import it into this stack before" in readme
    assert "proposes creating or replacing an already-live VPN record" in compact_readme
    assert "remain `proxied = false`" in readme
    assert 'cloudflare_dns_record.this["de-3-vpn-ipv4"]' in readme
    assert 'cloudflare_dns_record.this["de-3-vpn-ipv6"]' in readme
    assert "cd8f1c0984db4c3ce3171eca0c7396b1" in readme
    assert "00a3ab1a6fd0de22b555d0a68ee48446" in readme
    assert 'index("create") | not' in readme
    assert 'index("delete") | not' in readme
    assert 'select(.mode == "managed")' in readme
    assert 'else .actions == ["no-op"]' in readme
