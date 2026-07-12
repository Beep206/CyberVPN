# ruff: noqa: S101

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_ROOT = REPO_ROOT / "infra"
ROLE = INFRA_ROOT / "ansible" / "roles" / "spb_listener_ipv6_address"

DEFAULTS = ROLE / "defaults" / "main.yml"
VALIDATE = ROLE / "tasks" / "validate.yml"
DEPLOY = ROLE / "tasks" / "deploy.yml"
VERIFY = ROLE / "tasks" / "verify.yml"
ROLLBACK = ROLE / "tasks" / "rollback.yml"
SERVICE_TEMPLATE = ROLE / "templates" / "cybervpn-spb-listener-ipv6.service.j2"
SCRIPT_TEMPLATE = ROLE / "templates" / "cybervpn-spb-listener-ipv6.sh.j2"
PLAYBOOK = INFRA_ROOT / "ansible" / "playbooks" / "spb-listener-ipv6-address.yml"
PRODUCTION_INVENTORY = (
    INFRA_ROOT / "ansible" / "inventories" / "production" / "hosts.yml"
)
DNS_EXAMPLE = (
    INFRA_ROOT
    / "terraform"
    / "live"
    / "production"
    / "dns"
    / "terraform.tfvars.example"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_manager(tmp_path: Path, fake_ip: Path) -> Path:
    environment = Environment(
        loader=FileSystemLoader(str(SCRIPT_TEMPLATE.parent)),
        autoescape=False,
    )
    script = tmp_path / "cybervpn-spb-listener-ipv6"
    script.write_text(
        environment.get_template(SCRIPT_TEMPLATE.name).render(
            spb_listener_ipv6_address_ip_binary=str(fake_ip),
            spb_listener_ipv6_address_interface="eth0",
            spb_listener_ipv6_address_address="2a01:e5c0:1368::3",
            spb_listener_ipv6_address_prefix_length=48,
            spb_listener_ipv6_address_expected_prefix="2a01:e5c0:1368::/48",
            spb_listener_ipv6_address_state_dir=str(tmp_path / "run"),
            spb_listener_ipv6_address_dad_wait_attempts=1,
            spb_listener_ipv6_address_dad_wait_seconds=0,
        ),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _fake_ip(tmp_path: Path) -> Path:
    fake = tmp_path / "ip"
    fake.write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu
            state="absent"
            if [ -f "$FAKE_IP_STATE" ]; then
              state="$(cat "$FAKE_IP_STATE")"
            fi
            printf '%s\\n' "$*" >>"$FAKE_IP_LOG"
            target="2a01:e5c0:1368::3/48"

            target_line() {
              case "$state" in
                absent) ;;
                dadfailed)
                  printf '2: eth0    inet6 %s scope global dadfailed\\n' "$target"
                  ;;
                tentative)
                  printf '2: eth0    inet6 %s scope global tentative\\n' "$target"
                  ;;
                *)
                  printf '2: eth0    inet6 %s scope global\\n' "$target"
                  ;;
              esac
            }

            case "$*" in
              "-o link show dev eth0")
                printf '2: eth0: <BROADCAST,UP> mtu 1500\\n'
                ;;
              "-6 route show default")
                if [ "${FAKE_IP_SCENARIO:-success}" = "route-change" ] &&
                   [ "$state" != "absent" ]; then
                  printf 'default via fe80::2 dev eth0\\n'
                else
                  printf 'default via fe80::1 dev eth0\\n'
                fi
                ;;
              "-6 -o addr show dev eth0 scope global")
                target_line
                ;;
              "-6 -o addr show scope global")
                target_line
                ;;
              "-o addr show dev eth0")
                printf '2: eth0    inet 193.233.91.99/24 scope global eth0\\n'
                target_line
                ;;
              "-6 addr replace 2a01:e5c0:1368::3/48 dev eth0 noprefixroute")
                case "${FAKE_IP_SCENARIO:-success}" in
                  dadfailed) printf 'dadfailed' >"$FAKE_IP_STATE" ;;
                  tentative) printf 'tentative' >"$FAKE_IP_STATE" ;;
                  *) printf 'added' >"$FAKE_IP_STATE" ;;
                esac
                ;;
              "-6 addr del 2a01:e5c0:1368::3/48 dev eth0")
                printf 'absent' >"$FAKE_IP_STATE"
                ;;
              *)
                printf 'unexpected fake ip command: %s\\n' "$*" >&2
                exit 64
                ;;
            esac
            """
        ),
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return fake


def _run_manager(
    tmp_path: Path,
    *,
    action: str = "ensure",
    scenario: str = "success",
    initial_state: str = "absent",
    owned: bool = False,
) -> tuple[subprocess.CompletedProcess[str], str]:
    if not Path("/bin/sh").exists():
        pytest.skip("rendered shell manager execution requires /bin/sh")
    state = tmp_path / "state"
    state.write_text(initial_state, encoding="utf-8")
    log = tmp_path / "ip.log"
    fake_ip = _fake_ip(tmp_path)
    script = _render_manager(tmp_path, fake_ip)
    marker_dir = tmp_path / "run"
    marker_dir.mkdir(exist_ok=True)
    if owned:
        (marker_dir / "owned").write_text(
            "2a01:e5c0:1368::3/48\n",
            encoding="utf-8",
        )

    env = os.environ.copy()
    env.update(
        {
            "FAKE_IP_STATE": str(state),
            "FAKE_IP_LOG": str(log),
            "FAKE_IP_SCENARIO": scenario,
        }
    )
    result = subprocess.run(
        ["/bin/sh", str(script), action],
        check=False,
        capture_output=True,
        encoding="utf-8",
        env=env,
    )
    return result, log.read_text(encoding="utf-8")


def test_role_defaults_pin_task2_spb_listener_contract() -> None:
    defaults = _read(DEFAULTS)
    validate = _read(VALIDATE)

    assert "spb_listener_ipv6_address_enabled: false" in defaults
    assert 'spb_listener_ipv6_address_expected_host_ipv4: "193.233.91.99"' in defaults
    assert 'spb_listener_ipv6_address_address: "2a01:e5c0:1368::3"' in defaults
    assert "spb_listener_ipv6_address_prefix_length: 48" in defaults
    assert (
        'spb_listener_ipv6_address_expected_prefix: "2a01:e5c0:1368::/48"' in defaults
    )
    assert "spb_listener_ipv6_address_unit_memory_max: 32M" in defaults
    assert "spb_listener_ipv6_address_unit_tasks_max: 32" in defaults
    assert "spb_listener_ipv6_address_state_dir" in defaults
    assert "spb_listener_ipv6_address_dad_wait_attempts: 10" in defaults

    assert (
        "ansible_host | default('') == spb_listener_ipv6_address_expected_host_ipv4"
        in validate
    )
    assert "groups.get(spb_listener_ipv6_address_target_group" in validate
    assert "| length) == 1" in validate
    assert "inventory_hostname in" in validate
    assert "spb_listener_ipv6_address_address == '2a01:e5c0:1368::3'" in validate
    assert "spb_listener_ipv6_address_prefix_length | int == 48" in validate
    assert (
        "spb_listener_ipv6_address_expected_prefix == '2a01:e5c0:1368::/48'" in validate
    )
    assert "spb_listener_ipv6_address_cidr == '2a01:e5c0:1368::3/48'" in validate
    assert "spb_listener_ipv6_address_interface != 'lo'" in validate
    assert "^(docker|br-|veth|virbr|tun|tap|wg|tailscale|zt)" in validate
    assert "safe absolute paths" in validate


def test_systemd_oneshot_is_hardened_and_has_removal_action() -> None:
    service = _read(SERVICE_TEMPLATE)
    script = _read(SCRIPT_TEMPLATE)
    deploy = _read(DEPLOY)
    verify = _read(VERIFY)
    rollback = _read(ROLLBACK)
    playbook = _read(PLAYBOOK)

    assert "Type=oneshot" in service
    assert "RemainAfterExit=yes" in service
    assert "ExecStart={{ spb_listener_ipv6_address_script_path }} ensure" in service
    assert "ExecStop={{ spb_listener_ipv6_address_script_path }} remove" in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectSystem=strict" in service
    assert "RestrictAddressFamilies=AF_INET AF_INET6 AF_NETLINK" in service
    assert "CapabilityBoundingSet=CAP_NET_ADMIN" in service
    assert (
        "RuntimeDirectory={{ spb_listener_ipv6_address_runtime_directory }}" in service
    )
    assert "ReadWritePaths={{ spb_listener_ipv6_address_state_dir }}" in service
    assert "MemoryMax={{ spb_listener_ipv6_address_unit_memory_max }}" in service
    assert "TasksMax={{ spb_listener_ipv6_address_unit_tasks_max }}" in service
    assert deploy.count("when: not ansible_check_mode") == 2
    assert "- not ansible_check_mode" in _read(ROLE / "tasks" / "main.yml")
    assert "ExecStart={{ spb_listener_ipv6_address_script_path }} ensure" in service
    assert "ExecStop={{ spb_listener_ipv6_address_script_path }} remove" in service

    assert "default_routes()" in script
    assert 'fail "IPv6 default routes changed during $ACTION"' in script
    assert "non_target_addresses()" in script
    assert "all_target_prefixes()" in script
    assert "wait_for_target_usable()" in script
    assert "dadfailed" in script
    assert "refusing to take over pre-existing unmanaged listener address" in script
    assert "cleanup_on_error()" in script
    assert "unexpected interface or prefix" in script
    assert 'fail "non-target interface addresses changed during $ACTION"' in script
    assert '"$IP_BIN" -6 addr replace "$CIDR" dev "$INTERFACE" noprefixroute' in script
    assert '"$IP_BIN" -6 addr del "$CIDR" dev "$INTERFACE"' in script
    assert "noprefixroute" in script
    assert "route add" not in script
    assert "route del" not in script
    assert "route replace" not in script
    assert "addr flush" not in script

    assert "systemd-analyze" in deploy
    assert "Check target address is not on another interface" in deploy
    assert "regex_escape" in deploy
    assert "systemd_service" in deploy
    assert "enabled: true" in deploy
    assert "state: started" in deploy
    assert "systemd-analyze" in verify
    assert "systemctl" in verify
    assert "is-enabled" in verify
    assert "is-active" in verify
    assert "dadfailed|tentative|deprecated" in verify
    assert "spb_listener_ipv6_address_state_dir }}/owned" in verify
    assert "b64decode | trim" in verify
    assert "state: stopped" in rollback
    assert "spb_listener_ipv6_address_script_path" in rollback
    assert "remove" in rollback
    assert "state: absent" in rollback
    assert "spb_listener_ipv6_address_state_dir" in rollback
    assert "default('spb_listener_ipv6_address')" in playbook
    assert "Refuse silent no-op apply" in playbook
    assert "role: spb_listener_ipv6_address" in playbook


def test_rendered_manager_converges_idempotently_with_fake_ip(tmp_path: Path) -> None:
    first, first_log = _run_manager(tmp_path)
    assert first.returncode == 0, first.stderr
    assert "addr replace 2a01:e5c0:1368::3/48 dev eth0 noprefixroute" in first_log
    assert (tmp_path / "run" / "owned").read_text(encoding="utf-8").strip() == (
        "2a01:e5c0:1368::3/48"
    )

    second, second_log = _run_manager(tmp_path, initial_state="added", owned=True)
    assert second.returncode == 0, second.stderr
    assert second_log.count("addr replace 2a01:e5c0:1368::3/48") == 1


def test_rendered_manager_refuses_unmanaged_preexisting_target(
    tmp_path: Path,
) -> None:
    result, log = _run_manager(tmp_path, initial_state="preexisting")
    assert result.returncode != 0
    assert "pre-existing unmanaged listener address" in result.stderr
    assert "addr replace 2a01:e5c0:1368::3/48" not in log


def test_rendered_manager_cleans_up_new_target_on_route_drift(
    tmp_path: Path,
) -> None:
    result, log = _run_manager(tmp_path, scenario="route-change")
    assert result.returncode != 0
    assert "IPv6 default routes changed during ensure" in result.stderr
    assert "addr replace 2a01:e5c0:1368::3/48 dev eth0 noprefixroute" in log
    assert "addr del 2a01:e5c0:1368::3/48 dev eth0" in log


def test_rendered_manager_rejects_dadfailed_and_cleans_up(
    tmp_path: Path,
) -> None:
    result, log = _run_manager(tmp_path, scenario="dadfailed")
    assert result.returncode != 0
    assert "duplicate-address detection" in result.stderr
    assert "addr del 2a01:e5c0:1368::3/48 dev eth0" in log


def test_rendered_manager_refuses_to_remove_unmanaged_target(
    tmp_path: Path,
) -> None:
    result, log = _run_manager(tmp_path, action="remove", initial_state="preexisting")
    assert result.returncode != 0
    assert "refusing to remove unmanaged listener address" in result.stderr
    assert "addr del 2a01:e5c0:1368::3/48" not in log


def test_production_inventory_has_dedicated_spb_listener_group_and_vars() -> None:
    inventory = yaml.safe_load(_read(PRODUCTION_INVENTORY))

    groups = inventory["all"]["children"]
    assert "spb_listener_ipv6_address" in groups
    listener_group = groups["spb_listener_ipv6_address"]
    assert listener_group["hosts"] == {"s1-ru-spb-3": {}}
    assert listener_group["vars"] == {
        "spb_listener_ipv6_address_enabled": True,
        "spb_listener_ipv6_address_interface": "enp0s3",
        "spb_listener_ipv6_address_address": "2a01:e5c0:1368::3",
        "spb_listener_ipv6_address_prefix_length": 48,
        "spb_listener_ipv6_address_expected_prefix": "2a01:e5c0:1368::/48",
    }
    assert (
        groups["remnawave_edge_production"]["hosts"]["s1-ru-spb-3"]["ansible_host"]
        == "193.233.91.99"
    )


def test_dns_example_keeps_bridge_ipv6_out_of_public_task2_dns() -> None:
    example = _read(DNS_EXAMPLE)

    assert "spb-exceptions-vpn-ipv4" in example
    assert "spb-exceptions-vpn-ipv6" not in example
    assert example.count('name         = "spb-exceptions.cyber-vpn.org"') == 1
    assert 'content      = "193.233.91.99"' in example
    task2_record = example.split("spb-exceptions-vpn-ipv4 = {", 1)[1].split("}", 1)[0]
    assert 'record_class = "vpn-node"' in task2_record
    assert 'type         = "A"' in task2_record
    assert "ttl          = 300" in task2_record
    assert "proxied      = false" in task2_record
    assert "node         =" not in task2_record
    assert "tags         =" not in task2_record
