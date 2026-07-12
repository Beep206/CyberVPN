# ruff: noqa: S101

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_ROOT = REPO_ROOT / "infra"
ROLE = INFRA_ROOT / "ansible" / "roles" / "spb_de_exceptions_bridge"

DEFAULTS = ROLE / "defaults" / "main.yml"
VALIDATE = ROLE / "tasks" / "validate.yml"
DEPLOY = ROLE / "tasks" / "deploy.yml"
VERIFY = ROLE / "tasks" / "verify.yml"
ROLLBACK = ROLE / "tasks" / "rollback.yml"
NFTABLES_TEMPLATE = ROLE / "templates" / "nftables.conf.j2"
FIREWALL_TEMPLATE = (
    ROLE / "templates" / "cybervpn-spb-de-exceptions-firewall.service.j2"
)
PLAYBOOK = INFRA_ROOT / "ansible" / "playbooks" / "spb-de-exceptions-bridge.yml"
GROUP_VARS_EXAMPLE = (
    INFRA_ROOT
    / "ansible"
    / "inventories"
    / "production"
    / "group_vars"
    / "spb_de_exceptions_bridge"
    / "main.yml.example"
)
GROUP_VARS_PRODUCTION = GROUP_VARS_EXAMPLE.with_name("main.yml")

SYSTEMD_FIREWALL = (
    INFRA_ROOT / "systemd" / "cybervpn-spb-de-exceptions-firewall.service"
)
SYSTEMD_PREFLIGHT = (
    INFRA_ROOT / "systemd" / "cybervpn-spb-de-exceptions-port-preflight.service"
)
SYSTEMD_README = INFRA_ROOT / "systemd" / "README.spb-de-exceptions.md"

SEED = REPO_ROOT / "scripts" / "remnawave" / "seed-cybervpn-spb-de-exceptions.sql"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "SPB_DE_EXCEPTIONS_ROLLBACK.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ansible_role_defaults_are_disabled_and_pinned_to_task2_contract() -> None:
    defaults = _read(DEFAULTS)
    validate = _read(VALIDATE)
    group_vars = _read(GROUP_VARS_EXAMPLE)
    production_group_vars = _read(GROUP_VARS_PRODUCTION)

    assert "spb_de_exceptions_bridge_enabled: false" in defaults
    assert "spb_de_exceptions_bridge_port: 9444" in defaults
    assert (
        "spb_de_exceptions_bridge_inbound_tag: DE_SPB_EXCEPTIONS_BRIDGE_9444"
        in defaults
    )
    assert "spb_de_exceptions_bridge_outbound_tag: DE_EXCEPTIONS_BRIDGE" in defaults
    assert (
        "spb_de_exceptions_bridge_product_code: premium_spb_de_exceptions" in defaults
    )
    assert "spb_de_exceptions_bridge_run_port_preflight: true" in defaults
    assert "spb_de_exceptions_bridge_allowed_ipv4_cidrs: []" in defaults
    assert "2a01:e5c0:1368::3/128" in defaults
    assert "0.0.0.0/0" not in defaults
    assert "::/0" not in defaults

    assert "spb_de_exceptions_bridge_port | int == 9444" in validate
    assert "DE_SPB_EXCEPTIONS_BRIDGE_9444" in validate
    assert "DE_EXCEPTIONS_BRIDGE" in validate
    assert "premium_spb_de_exceptions" in validate
    assert "IPv4 bridge path is disabled" in validate
    assert "/32$" in validate
    assert "/128$" in validate
    assert "nftables peer-only firewall management" in validate

    assert "spb_de_exceptions_bridge_enabled: false" in group_vars
    assert "2a01:e5c0:1368::3/128" in group_vars
    assert "Do not store real secrets" in group_vars
    assert "spb_de_exceptions_bridge_enabled: true" in production_group_vars
    assert "spb_de_exceptions_bridge_port: 9444" in production_group_vars
    assert "spb_de_exceptions_bridge_allowed_ipv4_cidrs: []" in production_group_vars
    assert "2a01:e5c0:1368::3/128" in production_group_vars
    assert "0.0.0.0/0" not in production_group_vars
    assert "::/0" not in production_group_vars


def test_ansible_firewall_renders_peer_only_tcp_and_udp_9444() -> None:
    nftables = _read(NFTABLES_TEMPLATE)
    deploy = _read(DEPLOY)
    verify = _read(VERIFY)
    rollback = _read(ROLLBACK)
    firewall_unit = _read(FIREWALL_TEMPLATE)

    assert (
        "tcp dport {{ spb_de_exceptions_bridge_port }} ip saddr @spb_ipv4 accept"
        in nftables
    )
    assert (
        "udp dport {{ spb_de_exceptions_bridge_port }} ip saddr @spb_ipv4 accept"
        in nftables
    )
    assert (
        "tcp dport {{ spb_de_exceptions_bridge_port }} ip6 saddr @spb_ipv6 accept"
        in nftables
    )
    assert (
        "udp dport {{ spb_de_exceptions_bridge_port }} ip6 saddr @spb_ipv6 accept"
        in nftables
    )
    assert "tcp dport {{ spb_de_exceptions_bridge_port }} counter drop" in nftables
    assert "udp dport {{ spb_de_exceptions_bridge_port }} counter drop" in nftables
    assert 'iifname "lo"' not in nftables
    assert "0.0.0.0/0" not in nftables
    assert "::/0" not in nftables

    assert "system: true" in deploy
    assert "shell: /usr/sbin/nologin" in deploy
    assert "groups: []" in deploy
    assert "append: false" in deploy
    assert "Assert bridge port is free before first activation" in deploy
    assert "spb_de_exceptions_bridge_run_port_preflight | bool" in deploy
    assert "nft" in deploy
    assert "-c" in deploy
    assert "community.general.ufw" in deploy
    assert "proto: tcp" in deploy
    assert "proto: udp" in deploy
    assert 'to_port: "{{ spb_de_exceptions_bridge_port }}"' in deploy
    assert "Remove deprecated IPv4 bridge TCP allows" in deploy
    assert "Remove deprecated IPv4 bridge UDP allows" in deploy
    assert "register: spb_de_exceptions_bridge_nft_template" in deploy
    assert "register: spb_de_exceptions_bridge_firewall_unit_template" in deploy
    assert "state: \"{{ 'restarted' if" in deploy
    assert deploy.count("- not ansible_check_mode") == 2
    assert "9443" not in deploy

    assert "'tcp dport 9444' in spb_de_exceptions_bridge_nft_output.stdout" in verify
    assert "'udp dport 9444' in spb_de_exceptions_bridge_nft_output.stdout" in verify
    assert "tcp dport 9444 counter .* drop" in verify
    assert "udp dport 9444 counter .* drop" in verify
    assert "sport = :{{ spb_de_exceptions_bridge_port }}" in rollback
    assert "Refuse firewall rollback while bridge port is listening" in rollback
    assert (
        "failed_when: spb_de_exceptions_bridge_port_listeners.stdout | trim | length > 0"
        in rollback
    )
    assert "Check nftables table presence" in rollback
    assert "spb_de_exceptions_bridge_nft_table_status.rc != 0" in rollback
    assert (
        "'No such file' not in spb_de_exceptions_bridge_nft_table_status.stderr"
        in rollback
    )
    assert "spb_de_exceptions_bridge_nft_table_status.rc == 0" in rollback
    assert "delete" in rollback
    assert "Remove bridge TCP UFW allow rule" in rollback
    assert "Remove bridge UDP UFW allow rule" in rollback
    assert "delete: true" in rollback
    assert "failed_when: false" not in rollback
    assert "spb_de_exceptions_bridge_nftables_table_name" in rollback

    assert "Before=remnanode.service remnanode@.service" in firewall_unit
    assert "ConditionPathExists" not in firewall_unit
    assert (
        "RequiresMountsFor={{ spb_de_exceptions_bridge_nftables_include_dir }}"
        in firewall_unit
    )
    assert "RequiredBy=remnanode.service remnanode@.service" in firewall_unit
    assert "ExecStartPre=/usr/sbin/nft -c -f" in firewall_unit
    assert (
        "ExecStartPre=-/usr/sbin/nft delete table inet "
        "{{ spb_de_exceptions_bridge_nftables_table_name }}" in firewall_unit
    )
    assert "NoNewPrivileges=true" in firewall_unit
    assert "ProtectSystem=strict" in firewall_unit
    assert "RestrictAddressFamilies=AF_INET AF_INET6 AF_NETLINK" in firewall_unit
    assert "MemoryMax={{ spb_de_exceptions_bridge_unit_memory_max }}" in firewall_unit


def test_playbook_targets_dedicated_role_only() -> None:
    playbook = _read(PLAYBOOK)

    assert "spb_de_exceptions_bridge_target_group" in playbook
    assert "default('spb_de_exceptions_bridge')" in playbook
    assert "role: spb_de_exceptions_bridge" in playbook
    assert "remnawave_edge" not in playbook


def test_systemd_units_are_hardened_and_do_not_proxy_bridge_traffic() -> None:
    firewall = _read(SYSTEMD_FIREWALL)
    preflight = _read(SYSTEMD_PREFLIGHT)
    readme = _read(SYSTEMD_README)

    for unit in (firewall, preflight):
        assert "NoNewPrivileges=true" in unit
        assert "ProtectSystem=strict" in unit
        assert "PrivateTmp=true" in unit
        assert "MemoryMax=64M" in unit
        assert "TasksMax=64" in unit
        assert "systemd-socket-proxyd" not in unit

    assert "Before=remnanode.service remnanode@.service" in firewall
    assert "ConditionPathExists" not in firewall
    assert "RequiresMountsFor=/etc/nftables.d" in firewall
    assert "RequiredBy=remnanode.service remnanode@.service" in firewall
    assert "Before=remnanode.service remnanode@.service" not in preflight
    assert "[Install]" not in preflight
    assert "WantedBy=" not in preflight
    assert "ExecStartPre=/usr/sbin/nft -c -f" in firewall
    assert (
        "ExecStartPre=-/usr/sbin/nft delete table inet "
        "cybervpn_spb_de_exceptions_bridge" in firewall
    )
    assert "/etc/nftables.d/cybervpn-spb-de-exceptions-bridge.nft" in firewall
    assert "sport = :9444" in preflight
    assert "already in use" in preflight

    assert "does not implement the VPN bridge traffic" in readme
    assert "must not be enabled" in readme
    assert "not ordered into boot or Remnanode restart" in readme
    assert "DE_SPB_EXCEPTIONS_BRIDGE_9444" in readme
    assert "DE_EXCEPTIONS_BRIDGE" in readme
    assert "2a01:e5c0:1368::3/128" in readme
    assert "2a0b:4140:ba84::2" in readme
    assert "DE first" in readme
    assert "SPB" in readme
    assert "No credentials" in readme


def test_seed_is_task2_only_and_keeps_bridge_out_of_customer_scope() -> None:
    seed = _read(SEED)
    mihomo_template = seed.split("$cybervpn_spb_de_exceptions_yaml$", 2)[1]

    assert "CYBERVPN_SPB_DE_EXCEPTIONS" in seed
    assert "CYBERVPN_SPB_DE_NODES" in seed
    assert "CYBERVPN_SPB_DE_BRIDGE" in seed
    assert "DE_SPB_EXCEPTIONS_BRIDGE_9444" in seed
    assert "premium_spb_de_exceptions" in seed
    assert "premium_smart_ru" not in seed
    assert "CYBERVPN_PREMIUM_SMART_RU" not in seed
    assert "bridge_inbound_customer_cleanup" in seed
    assert "Task2 customer squad must not contain the DE bridge inbound" in seed
    assert (
        "Task2 MIHOMO customer template must not expose DIRECT as a proxy choice"
        in seed
    )
    assert "- DIRECT" not in mihomo_template
    assert "DIRECT" not in mihomo_template
    assert "password" not in seed.lower()
    assert "REMNAWAVE_TOKEN" not in seed


def test_runbook_documents_secret_safe_dry_run_apply_and_rollback_boundaries() -> None:
    runbook = _read(RUNBOOK)

    assert "does not authorize production mutation by itself" in runbook
    assert "Dry-run is the default" in runbook
    assert "bridgePortFree" in runbook
    assert "bridgePublicHost" in runbook
    assert "mode `0600`" in runbook
    assert "--spb-task2-listen-address" in runbook
    assert "duplicate address/port pair" in runbook
    assert "Switch and restart DE first" in runbook
    assert "Restart SPB" in runbook
    assert "Restore remapped shared SPB Host snapshots" in runbook
    assert "Restore remapped shared DE Host snapshots" in runbook
    assert "fall through to SPB `DIRECT`" in runbook
    assert "Remnawave tokens" in runbook
    assert "bridge passwords" in runbook
    assert "VLESS UUID values" in runbook
    assert "rollback manifest contents" in runbook


def test_spb_task2_dedicated_public_ports_are_declared_in_firewall_iac() -> None:
    inventory = _read(INFRA_ROOT / "ansible/inventories/production/hosts.yml")
    defaults = _read(INFRA_ROOT / "ansible/roles/remnawave_edge/defaults/main.yml")
    deploy = _read(INFRA_ROOT / "ansible/roles/remnawave_edge/tasks/deploy.yml")

    spb = inventory.split("s1-ru-spb-3:", 1)[1].split("s1-nl-4:", 1)[0]
    assert "remnawave_edge_public_ingress_rules:" in spb
    assert "port: 4443" in spb
    assert "port: 8444" in spb
    assert "remnawave_edge_public_ingress_rules: []" in defaults
    assert "Remnawave | Validate public ingress rules" in deploy
    assert "Remnawave | Allow public ingress" in deploy
    assert "community.general.ufw" in deploy
