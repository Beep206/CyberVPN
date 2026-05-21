# Stage 1 Rented Production Server Rental Evidence

Date: `2026-05-19T16:04:11Z`

Stage: `STAGE1-RENT-01`

Scope: first connection and read-only baseline for `prod-app-1`

## Server

| Field | Value |
|---|---|
| Role | `prod-app-1` |
| Plan | `VPS X16` |
| RAM | `16 GB DDR4` |
| CPU | `6 CPU cores` |
| Disk | `240 GB SSD` |
| Bandwidth | `25 TB` |
| IPv4 | `45.87.41.146` |
| IPv6 allocation | `2a0d:2787:1b:12f5::/64` |

## SSH Attempt Result

Result:

```text
PASS: SSH key access works after locally normalizing MainKey2 into a PEM RSA private key.
```

What was tested:

| User | Key | Result |
|---|---|---|
| `root` | `~/.ssh/id_ed25519` | `Permission denied (publickey)` |
| `root` | `~/.ssh/vpn_ozoxy_wsl` | `Permission denied (publickey)` |
| `ubuntu` | `~/.ssh/id_ed25519` | `Permission denied (publickey)` |
| `ubuntu` | `~/.ssh/vpn_ozoxy_wsl` | `Permission denied (publickey)` |
| `debian` | `~/.ssh/id_ed25519` | `Permission denied (publickey)` |
| `debian` | `~/.ssh/vpn_ozoxy_wsl` | `Permission denied (publickey)` |
| `admin` | `~/.ssh/id_ed25519` | `Permission denied (publickey)` |
| `admin` | `~/.ssh/vpn_ozoxy_wsl` | `Permission denied (publickey)` |
| `beep` | `~/.ssh/id_ed25519` | `Permission denied (publickey)` |
| `beep` | `~/.ssh/vpn_ozoxy_wsl` | `Permission denied (publickey)` |
| `root` | `~/.ssh/MainKey2_private` | local key load failed: `error in libcrypto` |
| `root` | `~/.ssh/MainKey2_private_fixed.pem` | `PASS` |

`MainKey2_private` file observations:

```text
file type: OpenSSH private key
line endings: CRLF present
after LF copy: still fails to load with OpenSSH
ssh-keygen -y: error in libcrypto
```

The key material was structurally parsed and re-encoded locally into:

```text
~/.ssh/MainKey2_private_fixed.pem
```

The fixed PEM key derives the same public key fingerprint as `MainKey2_public`.

Public key fingerprint for `MainKey2_public`:

```text
2048 SHA256:c7qFl4d3KfF3Y8m9ZRzbCnbyK0GAB0Jc6u4L4wUTiko no comment (RSA)
```

No private key material was copied into this evidence.

## Read-Only Host Baseline

Connection:

```text
connected_as=root
hostname=prod-app-1
```

OS:

```text
Ubuntu 24.04
Linux 6.8.0-106-generic x86_64
```

Resources:

```text
CPU: 6
Memory: 15Gi total, 15Gi available at check time
Swap: 0B
Root filesystem: 232G total, 230G available, 1% used
```

Network:

```text
ens3 IPv4: 45.87.41.146/24
ens3 IPv6: 2a0d:2787:1b:12f5::a/64
```

Listening TCP ports:

```text
22/tcp on 0.0.0.0 and [::]
systemd-resolved local DNS listeners on loopback
```

Current baseline notes:

```text
Docker: not installed
UFW: installed but inactive
Only SSH is publicly listening from the initial read-only check
```

## Current Decision

`prod-app-1` rental/spec selection is accepted and SSH access is working.

Next step:

```text
STAGE1-RENT-02: OS baseline and firewall
```
