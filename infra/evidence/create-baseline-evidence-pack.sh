#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

if [[ ${EUID} -ne 0 ]]; then
  echo "ERROR: run as root" >&2
  exit 1
fi

evidence_root="${EVIDENCE_ROOT:-/srv/storage/evidence}"
timestamp="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
host_name="$(hostname -f 2>/dev/null || hostname)"
pack_dir="${evidence_root}/releases/cybervpn-h-baseline-${timestamp}"
security_dir="${evidence_root}/security-scans/cybervpn-h-baseline-${timestamp}"

mkdir -p \
  "${evidence_root}/releases" \
  "${evidence_root}/backups" \
  "${evidence_root}/restores" \
  "${evidence_root}/security-scans" \
  "${evidence_root}/incidents" \
  "${pack_dir}/host" \
  "${pack_dir}/services" \
  "${pack_dir}/backups" \
  "${pack_dir}/observability" \
  "${pack_dir}/security" \
  "${pack_dir}/configs" \
  "${security_dir}"

capture() {
  local output_file="$1"
  shift
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n\n'
    "$@"
  } >"${output_file}" 2>&1 || {
    local rc=$?
    printf '\nexit_code=%s\n' "${rc}" >>"${output_file}"
    return 0
  }
}

capture_shell() {
  local output_file="$1"
  local command_text="$2"
  {
    printf '$ %s\n\n' "${command_text}"
    bash -o pipefail -c "${command_text}"
  } >"${output_file}" 2>&1 || {
    local rc=$?
    printf '\nexit_code=%s\n' "${rc}" >>"${output_file}"
    return 0
  }
}

cat >"${pack_dir}/README.md" <<EOF
# CyberVPN h Baseline Evidence Pack

Created: \`${timestamp}\`

Host: \`${host_name}\`

This pack captures the current CyberVPN home server state for release,
backup, restore, incident, and security evidence continuity.

Secrets are not copied into this pack. Secret files are represented only by
ownership and permission metadata.
EOF

if command -v jq >/dev/null 2>&1; then
  jq -n \
    --arg created_at_utc "$(date -u --iso-8601=seconds)" \
    --arg host "${host_name}" \
    --arg phase "Phase 19: Evidence Archive" \
    --arg evidence_root "${evidence_root}" \
    --arg pack_dir "${pack_dir}" \
    --arg security_dir "${security_dir}" \
    '{
      created_at_utc: $created_at_utc,
      host: $host,
      phase: $phase,
      evidence_root: $evidence_root,
      pack_dir: $pack_dir,
      security_scan_dir: $security_dir,
      schema: {
        releases: "release manifests, image digests, SBOM references, rollout evidence",
        backups: "backup logs and restic summaries",
        restores: "restore drill logs and results",
        "security-scans": "secret/dependency/container scan reports",
        incidents: "incident timelines, decisions, and postmortems"
      }
    }' >"${pack_dir}/manifest.json"
else
  cat >"${pack_dir}/manifest.json" <<EOF
{
  "created_at_utc": "$(date -u --iso-8601=seconds)",
  "host": "${host_name}",
  "phase": "Phase 19: Evidence Archive",
  "evidence_root": "${evidence_root}",
  "pack_dir": "${pack_dir}",
  "security_scan_dir": "${security_dir}"
}
EOF
fi

capture "${pack_dir}/host/hostnamectl.txt" hostnamectl
capture "${pack_dir}/host/uname.txt" uname -a
capture "${pack_dir}/host/os-release.txt" cat /etc/os-release
capture "${pack_dir}/host/date-timedatectl.txt" timedatectl
capture "${pack_dir}/host/uptime.txt" uptime
capture "${pack_dir}/host/free.txt" free -h
capture "${pack_dir}/host/lscpu.txt" lscpu
capture "${pack_dir}/host/lsblk.txt" lsblk -f
capture "${pack_dir}/host/df.txt" df -hT
capture "${pack_dir}/host/findmnt-srv.txt" findmnt -R /srv
capture "${pack_dir}/host/ip-brief.txt" ip -brief address
capture "${pack_dir}/host/ip-route.txt" ip route
capture_shell "${pack_dir}/host/listeners.txt" "ss -tulpn | sed -E 's/users:\\(\\([^)]*\\)\\)/users:(redacted-process)/g'"

capture "${pack_dir}/services/docker-info.txt" docker info
capture "${pack_dir}/services/docker-ps.txt" docker ps --no-trunc --format 'table {{.Names}}\t{{.Image}}\t{{.ID}}\t{{.Status}}\t{{.Ports}}'
capture_shell "${pack_dir}/services/docker-compose-ps.txt" 'for f in /srv/cybervpn-h/compose/*/compose.yml; do echo "## ${f}"; docker compose -f "${f}" ps; echo; done'
capture "${pack_dir}/services/systemd-running-services.txt" systemctl list-units --type=service --state=running --no-pager
capture "${pack_dir}/services/systemd-timers.txt" systemctl list-timers --all --no-pager

capture_shell "${pack_dir}/configs/cybervpn-h-file-index.txt" 'find /srv/cybervpn-h \( -path /srv/cybervpn-h/secrets -o -path /srv/cybervpn-h/secrets/\* \) -prune -o -printf "%M %u:%g %s %TY-%Tm-%TdT%TH:%TM %p\n" | sort'
capture_shell "${pack_dir}/configs/evidence-file-index.txt" 'find /srv/storage/evidence -maxdepth 4 -printf "%M %u:%g %s %TY-%Tm-%TdT%TH:%TM %p\n" | sort'

if [[ -r /srv/cybervpn-h/secrets/restic.env ]] && command -v restic >/dev/null 2>&1; then
  (
    set -a
    # shellcheck disable=SC1091
    . /srv/cybervpn-h/secrets/restic.env
    set +a
    export RESTIC_REPOSITORY RESTIC_PASSWORD RESTIC_CACHE_DIR
    capture "${pack_dir}/backups/restic-snapshots.txt" restic snapshots
    capture "${pack_dir}/backups/restic-stats.txt" restic stats --mode raw-data
  )
else
  echo "restic.env or restic command unavailable" >"${pack_dir}/backups/restic-unavailable.txt"
fi

capture_shell "${pack_dir}/backups/gitlab-backups.txt" 'find /srv/storage/backups/gitlab -maxdepth 1 -type f -printf "%TY-%Tm-%TdT%TH:%TM %s %p\n" 2>/dev/null | sort || true'
capture_shell "${pack_dir}/backups/sentry-backups.txt" 'find /srv/storage/backups/sentry -maxdepth 2 -type f -printf "%TY-%Tm-%TdT%TH:%TM %s %p\n" 2>/dev/null | sort | tail -200 || true'
capture_shell "${pack_dir}/backups/config-backup-evidence.txt" 'find /srv/cybervpn-h/evidence/backups -maxdepth 2 -type f -name summary.txt -print -exec cat {} \; 2>/dev/null || true'

capture_shell "${pack_dir}/observability/prometheus-targets.json" 'curl -fsS http://127.0.0.1:9090/api/v1/targets'
capture_shell "${pack_dir}/observability/prometheus-active-alerts.json" 'curl -fsS http://127.0.0.1:9090/api/v1/alerts'
capture_shell "${pack_dir}/observability/alertmanager-status.json" 'curl -fsS http://127.0.0.1:9093/api/v2/status'
capture_shell "${pack_dir}/observability/grafana-dashboard-files.txt" 'find /srv/cybervpn-h/configs/grafana/dashboards -maxdepth 1 -type f -name "*.json" -printf "%f %s\n" | sort'

capture "${pack_dir}/security/ufw-status.txt" ufw status verbose
capture "${pack_dir}/security/fail2ban-status.txt" fail2ban-client status
capture_shell "${pack_dir}/security/sshd-effective-security.txt" 'sshd -T | egrep "^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication|x11forwarding|maxauthtries|allowusers|authenticationmethods)"'
capture_shell "${pack_dir}/security/secret-file-permissions.txt" 'find /srv/cybervpn-h/secrets -maxdepth 2 -type f -printf "%m %u:%g %p\n" | sort'
capture_shell "${pack_dir}/security/docker-socket-mounts.txt" 'for id in $(docker ps -q); do docker inspect --format "{{.Name}} {{range .Mounts}}{{if eq .Source \"/var/run/docker.sock\"}}{{.Source}} -> {{.Destination}}{{end}}{{end}}" "${id}"; done | sed "/^\\S\\+ $/d"'

capture "${security_dir}/ufw-status.txt" ufw status verbose
capture "${security_dir}/fail2ban-status.txt" fail2ban-client status
capture_shell "${security_dir}/secret-file-permissions.txt" 'find /srv/cybervpn-h/secrets -maxdepth 2 -type f -printf "%m %u:%g %p\n" | sort'
capture_shell "${security_dir}/tool-availability.txt" 'for tool in trivy grype syft npm pip-audit gitleaks trufflehog; do if command -v "${tool}" >/dev/null 2>&1; then printf "%s installed: %s\n" "${tool}" "$(command -v "${tool}")"; else printf "%s missing\n" "${tool}"; fi; done'

{
  echo "# Evidence Tree"
  echo
  find "${evidence_root}" -maxdepth 3 -type d -printf '%M %u:%g %p\n' | sort
} >"${pack_dir}/evidence-tree.txt"

find "${pack_dir}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum >"${pack_dir}/checksums.sha256"
find "${security_dir}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum >"${security_dir}/checksums.sha256"

chmod -R u=rwX,g=rX,o= "${pack_dir}" "${security_dir}"

printf 'baseline_pack=%s\n' "${pack_dir}"
printf 'security_scan_dir=%s\n' "${security_dir}"
printf 'status=ok\n'
