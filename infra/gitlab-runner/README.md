# GitLab Runner Examples

These files are examples for the `h` GitLab instance. Do not copy real runner tokens into the repository.

Recommended runner split:

| Runner | Purpose | Privileged | Tags |
|---|---|---:|---|
| `cybervpn-h-docker-protected` | Normal CI jobs on protected refs | No | `h-docker`, `protected` |
| `cybervpn-h-dind-protected` | Future manual Docker build jobs | Yes | `dind` |

Phase 17 only enables `cybervpn-h-docker-protected`. The `.gitlab-ci.yml` Docker package jobs use the `dind` tag and are manual by design; keep them pending until a separate protected DIND runner is intentionally added.

## Current Normal Runner

Implemented on `10.10.10.34`:

```text
runner: cybervpn-h-docker-protected
url: https://gitlab.h.cyber-vpn.net
executor: docker
run_untagged: false
access_level: ref_protected
memory: 8g
memory_swap: 12g
cpus: 8
cache: /srv/storage/gitlab-cache
```

The real runner config contains an authentication token and lives on the server:

```text
/srv/cybervpn-h/secrets/gitlab-runner/config.toml
```

The repository should only contain sanitized examples.

## Future DIND Runner

Recommended policy if Docker-in-Docker is added later:

```text
executor: docker
default image: docker:27-cli
tags: dind
run untagged jobs: false
protected refs only: true
locked/manual jobs only: true
privileged: true
```

Do not enable privileged execution on the normal `h-docker` runner.
