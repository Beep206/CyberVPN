# CyberVPN — План внедрения Terraform + Ansible (IaC)

> **Версия:** 1.0 · **Дата:** 8 апреля 2026  
> **Статус:** Проектирование  
> **Целевые best practices:** Terraform 1.15+, Ansible 11+, Hetzner provider 1.60+, 2026

---

## Содержание

1. [Цели и обоснование](#1-цели-и-обоснование)
2. [Обзор выбранного стека](#2-обзор-выбранного-стека)
3. [Архитектура IaC](#3-архитектура-iac)
4. [Terraform — подробный план](#4-terraform--подробный-план)
5. [Ansible — подробный план](#5-ansible--подробный-план)
6. [Связка Terraform → Ansible](#6-связка-terraform--ansible)
7. [Secrets Management](#7-secrets-management)
8. [CI/CD интеграция](#8-cicd-интеграция)
9. [Тестирование IaC](#9-тестирование-iac)
10. [Day-2 Operations (эксплуатация)](#10-day-2-operations)
11. [Сценарии использования](#11-сценарии-использования)
12. [Безопасность](#12-безопасность)
13. [Структура файлов](#13-структура-файлов)
14. [Фазы реализации](#14-фазы-реализации)
15. [Риски и митигации](#15-риски-и-митигации)

---

## 1. Цели и обоснование

### 1.1 Текущие проблемы

| Проблема | Последствие |
|---|---|
| VPN-ноды создаются вручную через web-панели Hetzner/DO | 30+ минут на каждую новую ноду |
| Настройка ОС вручную (SSH, firewall, Docker) | Несогласованность конфигов между нодами |
| Обновление Remnawave Node — SSH на каждый сервер | При 10+ нодах — 1-2 часа рутины |
| DNS-записи добавляются вручную в Cloudflare | Риск человеческой ошибки |
| Нет воспроизводимости инфраструктуры | Невозможно восстановить всё с нуля |
| Секреты (Reality keys, UUID) в головах/чатах | Критический security risk |

### 1.2 Целевое состояние

```
git push → CI/CD → terraform plan → approve → terraform apply → ansible-playbook
                                                    ↓
                                        Новая VPN-нода готова за 5 минут
                                        с Docker, Remnawave, firewall, monitoring
```

### 1.3 Конкретные задачи под наш проект

- **Provisioning VPN-нод** — Hetzner VPS в разных локациях
- **Provisioning Helix Node** — edge-серверы для нашего собственного протокола
- **DNS Management** — A/AAAA записи в Cloudflare для каждой ноды
- **Массовое обновление** — `remnawave/node:2.7.4` → `2.8.x` на всех нодах одной командой
- **Helix rollout** — деплой helix-node daemon на edge-серверы
- **Security hardening** — унификация настроек SSH, UFW, Fail2ban
- **Monitoring agent** — установка node-exporter + promtail на каждую ноду
- **Backup** — автоматический бэкап конфигов нод

---

## 2. Обзор выбранного стека

### 2.1 Почему Terraform + Ansible (а не Pulumi / только Ansible)

| Критерий | Terraform + Ansible | Pulumi | Только Ansible |
|---|---|---|---|
| Разделение ответственности | ✅ Чёткое: create vs configure | ❌ Смешивает | ❌ Плохо создаёт ресурсы |
| State management | ✅ Terraform state с drift detection | ✅ Pulumi state | ❌ Нет state |
| Экосистема | ✅ Огромная, зрелая | ⚠️ Растущая | ✅ Ansible Galaxy |
| Найм DevOps | ✅ 90% знают | ⚠️ Нишевый | ✅ Знают |
| Наша команда (Python/Rust) | ✅ HCL прост + YAML привычен | ⚠️ Ещё один TS runtime | ✅ Python-friendly |
| Docker Compose деплой | ✅ Ansible `docker_compose_v2` | ⚠️ Нужен свой подход | ✅ Идеально |
| Hetzner provider | ✅ Зрелый (1.60+) | ⚠️ Менее зрелый | ⚠️ Через hcloud module |

### 2.2 Версии инструментов (2026 best practices)

| Инструмент | Минимальная версия | Почему |
|---|---|---|
| Terraform | ≥1.15 | Ephemeral values, variables в module sources |
| hetznercloud/hcloud provider | ≥1.60.0 | IP lifecycle changes (май 2026), `location` вместо `datacenter` |
| cloudflare/cloudflare provider | ≥5.x | Scoped API tokens, modern resource naming |
| Ansible | ≥11.0 (ansible-core ≥2.18) | Python 3.12+, performance improvements |
| community.docker collection | ≥4.0 | `docker_compose_v2` module, assume_yes support |
| community.hetzner collection | ≥3.0 | Полная поддержка Hetzner API v1 |
| Molecule | ≥25.x | molecule-plugins[docker], modern testing |

---

## 3. Архитектура IaC

### 3.1 Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  infra/                                                      │
│  ├── terraform/          ← Создание облачных ресурсов        │
│  └── ansible/            ← Настройка серверов                │
└──────────┬──────────────────────────────┬────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────┐          ┌──────────────────────┐
│  Terraform       │          │  Ansible             │
│                  │          │                      │
│  • Hetzner VPS   │  output  │  • Docker install    │
│  • Cloudflare DNS│───IP────▶│  • Remnawave Node    │
│  • Firewall rules│          │  • Helix Node        │
│  • SSH keys      │          │  • SSH hardening     │
│  • Volumes       │          │  • UFW + Fail2ban    │
│                  │          │  • Monitoring agents  │
└──────────────────┘          └──────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────────────────────────────────────┐
│              VPN Infrastructure                       │
│                                                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Node 1  │  │ Node 2  │  │ Node 3  │  │ Node N  │ │
│  │ Helsinki │  │ Frankfurt│  │ Amsterdam│  │ Tokyo   │ │
│  │ xray     │  │ xray     │  │ helix   │  │ xray    │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │
└──────────────────────────────────────────────────────┘
```

### 3.2 Принцип разделения (Separation of Concerns)

| Слой | Инструмент | Что делает | State |
|---|---|---|---|
| **Infrastructure** | Terraform | Создаёт VPS, DNS, firewall, SSH keys, volumes | Remote S3 (versioned, encrypted) |
| **Configuration** | Ansible | Настраивает ОС, ставит софт, деплоит Docker stacks | Stateless (idempotent) |
| **Application** | Docker Compose | Запускает контейнеры (Remnawave, Helix, monitoring) | Managed by Ansible |

---

## 4. Terraform — подробный план

### 4.1 Структура проекта

```
infra/terraform/
├── environments/
│   ├── production/
│   │   ├── main.tf              # Вызов модулей
│   │   ├── variables.tf         # Входные переменные
│   │   ├── outputs.tf           # Выходные значения (IP → Ansible)
│   │   ├── terraform.tfvars     # Значения переменных (НЕ в git)
│   │   ├── backend.tf           # Remote state config
│   │   └── versions.tf          # Provider version locks
│   └── staging/
│       ├── main.tf
│       └── ...
├── modules/
│   ├── vpn-node/                # Модуль: VPN-нода
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── helix-edge/              # Модуль: Helix edge node
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── dns-record/              # Модуль: Cloudflare DNS запись
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── firewall/                # Модуль: Hetzner Firewall
│   │   ├── main.tf
│   │   └── variables.tf
│   └── control-plane/           # Модуль: Основной сервер (Panel + DB)
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── tests/                       # Native Terraform tests
│   ├── vpn_node_test.tftest.hcl
│   └── dns_test.tftest.hcl
└── .terraform.lock.hcl          # Provider lock file (в git)
```

### 4.2 Модуль `vpn-node` — ключевой модуль

```hcl
# modules/vpn-node/main.tf

resource "hcloud_server" "vpn_node" {
  name        = var.node_name
  server_type = var.server_type  # cx22, cx32, cx42
  image       = "ubuntu-24.04"
  location    = var.location      # ⚠️ НЕ datacenter (deprecated July 2026)

  ssh_keys = var.ssh_key_ids

  labels = {
    project     = "cybervpn"
    role        = var.node_role    # "remnawave" | "helix"
    environment = var.environment
    managed_by  = "terraform"
  }

  # cloud-init: минимальная начальная настройка
  user_data = templatefile("${path.module}/cloud-init.yml.tpl", {
    ssh_port       = var.ssh_port
    admin_username = var.admin_username
  })

  lifecycle {
    # Не пересоздавать сервер при изменении cloud-init
    ignore_changes = [user_data]
  }
}

# Выделенный IPv4 (не теряется при пересоздании сервера)
resource "hcloud_primary_ip" "vpn_ip" {
  name          = "${var.node_name}-ipv4"
  type          = "ipv4"
  location      = var.location
  assignee_type = "server"
  assignee_id   = hcloud_server.vpn_node.id
  auto_delete   = false  # ⚠️ С мая 2026: unassign перед delete

  labels = {
    project    = "cybervpn"
    managed_by = "terraform"
  }
}

# Привязка firewall
resource "hcloud_firewall_attachment" "vpn_fw" {
  firewall_id = var.firewall_id
  server_ids  = [hcloud_server.vpn_node.id]
}
```

### 4.3 Модуль `dns-record`

```hcl
# modules/dns-record/main.tf

data "cloudflare_zone" "main" {
  name = var.domain  # "ozoxy.ru"
}

resource "cloudflare_record" "vpn_node" {
  zone_id = data.cloudflare_zone.main.id
  name    = var.subdomain         # "fi-01.vpn"
  content = var.ipv4_address
  type    = "A"
  ttl     = 300
  proxied = false  # ⚠️ DNS-only для VPN (не через Cloudflare proxy)

  comment = "Managed by Terraform — CyberVPN ${var.node_role} node"
}
```

### 4.4 Модуль `firewall`

```hcl
# modules/firewall/main.tf

resource "hcloud_firewall" "vpn_node" {
  name = "cybervpn-vpn-node"

  # SSH (кастомный порт)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = var.ssh_port
    source_ips = var.admin_ips  # Только наши IP
  }

  # HTTPS (VPN трафик: VLESS-Reality, XHTTP, Trojan)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # Hysteria2 (UDP)
  rule {
    direction  = "in"
    protocol   = "udp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # Node Exporter (только monitoring сервер)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "9100"
    source_ips = [var.monitoring_server_ip]
  }

  # Remnawave gRPC (Panel ↔ Node, только panel IP)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = var.remnawave_grpc_port
    source_ips = [var.panel_server_ip]
  }

  labels = {
    project    = "cybervpn"
    managed_by = "terraform"
  }
}
```

### 4.5 Remote State (S3-совместимый backend)

```hcl
# environments/production/backend.tf

terraform {
  backend "s3" {
    bucket   = "cybervpn-terraform-state"
    key      = "production/terraform.tfstate"
    region   = "eu-central-1"       # Hetzner Object Storage или AWS S3
    encrypt  = true

    # State locking (DynamoDB для AWS, или use_lockfile для S3-compatible)
    use_lockfile = true
  }
}
```

### 4.6 Outputs для Ansible

```hcl
# environments/production/outputs.tf

output "vpn_nodes" {
  description = "Map of VPN nodes for Ansible inventory"
  value = {
    for name, node in module.vpn_nodes : name => {
      ip          = node.ipv4_address
      location    = node.location
      role        = node.role
      server_type = node.server_type
    }
  }
}

output "ansible_inventory" {
  description = "Dynamic Ansible inventory in INI format"
  value = templatefile("${path.module}/inventory.tpl", {
    nodes       = module.vpn_nodes
    ssh_port    = var.ssh_port
    admin_user  = var.admin_username
  })
}
```

### 4.7 Ephemeral Values (Terraform 1.10+ best practice)

```hcl
# Секреты не сохраняются в state file
variable "hcloud_token" {
  type      = string
  sensitive = true
  ephemeral = true  # ⚠️ 2026 best practice: не попадает в state
}

variable "cloudflare_api_token" {
  type      = string
  sensitive = true
  ephemeral = true
}
```

---

## 5. Ansible — подробный план

### 5.1 Структура проекта

```
infra/ansible/
├── ansible.cfg                    # Глобальная конфигурация
├── requirements.yml               # Collections (community.docker, community.hetzner)
├── inventory/
│   ├── production/
│   │   ├── hosts.yml              # Статический инвентарь
│   │   ├── group_vars/
│   │   │   ├── all.yml            # Общие переменные
│   │   │   ├── vpn_nodes.yml      # Переменные для VPN-нод
│   │   │   ├── helix_nodes.yml    # Переменные для Helix-нод
│   │   │   └── vault.yml          # 🔐 Зашифрованные секреты (ansible-vault)
│   │   └── host_vars/
│   │       ├── fi-01.yml          # Per-node: UUID, Reality keys
│   │       └── de-01.yml
│   └── staging/
│       └── hosts.yml
├── roles/
│   ├── common/                    # Базовая настройка ОС
│   │   ├── tasks/
│   │   │   ├── main.yml
│   │   │   ├── ssh.yml            # SSH hardening
│   │   │   ├── firewall.yml       # UFW config
│   │   │   ├── packages.yml       # Обновления, основные пакеты
│   │   │   ├── fail2ban.yml       # Anti-bruteforce
│   │   │   ├── users.yml          # Системные пользователи
│   │   │   └── sysctl.yml         # Kernel tuning (net.core, tcp)
│   │   ├── handlers/main.yml
│   │   ├── templates/
│   │   │   ├── sshd_config.j2
│   │   │   ├── fail2ban.local.j2
│   │   │   └── sysctl.conf.j2
│   │   └── defaults/main.yml
│   ├── docker/                    # Установка Docker + Compose
│   │   ├── tasks/main.yml
│   │   └── handlers/main.yml
│   ├── remnawave-node/            # Деплой Remnawave Node
│   │   ├── tasks/
│   │   │   ├── main.yml
│   │   │   ├── deploy.yml
│   │   │   └── update.yml
│   │   ├── templates/
│   │   │   ├── docker-compose.yml.j2
│   │   │   └── .env.j2
│   │   └── defaults/main.yml
│   ├── helix-node/                # Деплой Helix Node daemon
│   │   ├── tasks/main.yml
│   │   ├── templates/
│   │   │   └── docker-compose.yml.j2
│   │   └── defaults/main.yml
│   ├── monitoring-agent/          # node-exporter + promtail
│   │   ├── tasks/main.yml
│   │   └── templates/
│   │       ├── docker-compose.monitoring.yml.j2
│   │       └── promtail-config.yml.j2
│   └── backup/                    # Автобэкап конфигов
│       ├── tasks/main.yml
│       └── templates/
│           └── backup-cron.j2
├── playbooks/
│   ├── site.yml                   # Полный деплой с нуля
│   ├── update-remnawave.yml       # Обновить Remnawave на всех нодах
│   ├── update-helix.yml           # Обновить Helix на всех нодах
│   ├── rollback-remnawave.yml     # Откат Remnawave
│   ├── add-node.yml               # Добавить одну ноду
│   ├── remove-node.yml            # Вывести ноду из эксплуатации
│   ├── rotate-keys.yml            # Ротация Reality/TLS ключей
│   ├── security-audit.yml         # Проверка безопасности всех нод
│   └── helix-canary-deploy.yml    # Канареечный деплой Helix
└── molecule/                      # Тестирование ролей
    ├── common/
    │   ├── molecule.yml
    │   ├── converge.yml
    │   └── verify.yml
    └── remnawave-node/
        ├── molecule.yml
        ├── converge.yml
        └── verify.yml
```

### 5.2 Роль `common` — SSH hardening + Firewall

```yaml
# roles/common/tasks/ssh.yml
- name: SSH | Deploy hardened sshd_config
  ansible.builtin.template:
    src: sshd_config.j2
    dest: /etc/ssh/sshd_config
    owner: root
    group: root
    mode: "0600"
    validate: "sshd -t -f %s"
  notify: restart sshd
  no_log: false

- name: SSH | Ensure password auth is disabled
  ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: "^#?PasswordAuthentication"
    line: "PasswordAuthentication no"
  notify: restart sshd

- name: SSH | Ensure root login is disabled
  ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: "^#?PermitRootLogin"
    line: "PermitRootLogin no"
  notify: restart sshd
```

```yaml
# roles/common/tasks/firewall.yml
# ⚠️ Порядок критичен: сначала SSH, потом enable
- name: UFW | Allow SSH
  community.general.ufw:
    rule: allow
    port: "{{ ssh_port }}"
    proto: tcp

- name: UFW | Allow HTTPS (VPN traffic)
  community.general.ufw:
    rule: allow
    port: "443"
    proto: tcp

- name: UFW | Allow Hysteria2 UDP
  community.general.ufw:
    rule: allow
    port: "443"
    proto: udp

- name: UFW | Allow node-exporter from monitoring
  community.general.ufw:
    rule: allow
    from_ip: "{{ monitoring_server_ip }}"
    port: "9100"
    proto: tcp

- name: UFW | Default deny incoming
  community.general.ufw:
    state: enabled
    default: deny
    direction: incoming
```

### 5.3 Роль `remnawave-node` — деплой VPN-ноды

```yaml
# roles/remnawave-node/tasks/deploy.yml
- name: Create node directory
  ansible.builtin.file:
    path: /opt/remnanode
    state: directory
    owner: root
    mode: "0750"

- name: Template docker-compose.yml
  ansible.builtin.template:
    src: docker-compose.yml.j2
    dest: /opt/remnanode/docker-compose.yml
    owner: root
    mode: "0640"
  no_log: true  # ⚠️ Содержит секреты

- name: Template .env
  ansible.builtin.template:
    src: .env.j2
    dest: /opt/remnanode/.env
    owner: root
    mode: "0600"
  no_log: true

- name: Deploy Remnawave Node via Docker Compose
  community.docker.docker_compose_v2:
    project_src: /opt/remnanode
    state: present
    pull: always
  register: compose_result

- name: Verify node is healthy
  ansible.builtin.uri:
    url: "http://localhost:{{ remnawave_metrics_port }}/health"
    return_content: true
  register: health_check
  retries: 10
  delay: 5
  until: health_check.status == 200
```

### 5.4 Playbook `update-remnawave.yml`

```yaml
# playbooks/update-remnawave.yml
---
- name: Update Remnawave Node on all VPN nodes
  hosts: vpn_nodes
  become: true
  serial: 1       # ⚠️ Rolling update: по одной ноде за раз
  max_fail_percentage: 0

  vars:
    remnawave_version: "{{ target_version | default('2.7.4') }}"

  pre_tasks:
    - name: Record pre-update image version
      community.docker.docker_image_info:
        name: "remnawave/node"
      register: pre_update_image

  tasks:
    - name: Pull new Remnawave Node image
      community.docker.docker_image_pull:
        name: "remnawave/node:{{ remnawave_version }}"

    - name: Update Docker Compose stack
      community.docker.docker_compose_v2:
        project_src: /opt/remnanode
        state: present
        pull: always

    - name: Wait for node to become healthy
      ansible.builtin.uri:
        url: "http://localhost:{{ remnawave_metrics_port }}/health"
      register: health
      retries: 15
      delay: 5
      until: health.status == 200

    - name: Verify node is connected to Panel
      ansible.builtin.uri:
        url: "http://localhost:{{ remnawave_metrics_port }}/health"
        return_content: true
      register: panel_check
      failed_when: "'connected' not in panel_check.content"

  post_tasks:
    - name: Log successful update
      ansible.builtin.debug:
        msg: "✅ {{ inventory_hostname }} updated to remnawave/node:{{ remnawave_version }}"
```

### 5.5 Kernel tuning для VPN-нод

```yaml
# roles/common/templates/sysctl.conf.j2
# CyberVPN — Optimized for high-throughput VPN proxy
# Managed by Ansible — do not edit manually

# TCP optimization
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0

# Connection tracking
net.netfilter.nf_conntrack_max = 1048576
net.nf_conntrack_max = 1048576

# Buffer sizes
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 87380 16777216

# BBR congestion control
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Keep-alive
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 10

# TUN/TAP for Helix (если node_role == 'helix')
{% if node_role == 'helix' %}
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
{% endif %}
```

---

## 6. Связка Terraform → Ansible

### 6.1 Dynamic Inventory из Terraform Output

```python
#!/usr/bin/env python3
# infra/ansible/inventory/terraform_inventory.py
"""
Dynamic Ansible inventory from Terraform state.
Usage: ansible-playbook -i inventory/terraform_inventory.py site.yml
"""
import json
import subprocess
import sys

def get_terraform_output():
    result = subprocess.run(
        ["terraform", "output", "-json"],
        capture_output=True, text=True,
        cwd="../terraform/environments/production"
    )
    return json.loads(result.stdout)

def build_inventory(tf_output):
    nodes = tf_output.get("vpn_nodes", {}).get("value", {})

    inventory = {
        "_meta": {"hostvars": {}},
        "vpn_nodes": {"hosts": []},
        "helix_nodes": {"hosts": []},
        "all": {"children": ["vpn_nodes", "helix_nodes"]}
    }

    for name, info in nodes.items():
        inventory["_meta"]["hostvars"][name] = {
            "ansible_host": info["ip"],
            "ansible_port": 22022,
            "node_location": info["location"],
            "node_role": info["role"],
        }

        group = "helix_nodes" if info["role"] == "helix" else "vpn_nodes"
        inventory[group]["hosts"].append(name)

    return inventory

if __name__ == "__main__":
    tf = get_terraform_output()
    print(json.dumps(build_inventory(tf), indent=2))
```

### 6.2 Makefile для удобства

```makefile
# infra/Makefile

.PHONY: plan apply provision update-nodes

# Terraform
plan:
	cd terraform/environments/production && terraform plan

apply:
	cd terraform/environments/production && terraform apply

# Ansible
provision:
	cd ansible && ansible-playbook -i inventory/terraform_inventory.py playbooks/site.yml

update-nodes:
	cd ansible && ansible-playbook -i inventory/terraform_inventory.py playbooks/update-remnawave.yml

# Full deploy: create + configure
deploy: apply provision

# Специфичные операции
add-node:
	cd terraform/environments/production && terraform apply -target=module.vpn_nodes["$(NODE)"]
	cd ansible && ansible-playbook -i inventory/terraform_inventory.py playbooks/add-node.yml --limit $(NODE)

helix-canary:
	cd ansible && ansible-playbook -i inventory/terraform_inventory.py playbooks/helix-canary-deploy.yml
```

---

## 7. Secrets Management

### 7.1 Ansible Vault

```bash
# Создание зашифрованного файла
ansible-vault create inventory/production/group_vars/vault.yml

# Содержимое vault.yml:
# vault_remnawave_panel_token: "eyJhbGciOiJIUzI1..."
# vault_reality_private_keys:
#   fi-01: "abc123..."
#   de-01: "def456..."
# vault_cloudflare_api_token: "cf-xxxx"
# vault_hcloud_token: "hc-xxxx"
```

### 7.2 Правила именования секретов

| Конвенция | Пример | Почему |
|---|---|---|
| Префикс `vault_` | `vault_reality_key` | Отличает от plain-text переменных |
| `no_log: true` | В каждой задаче с секретами | Не попадает в stdout CI/CD |
| Раздельные vault-файлы | `prod_vault.yml`, `staging_vault.yml` | Изоляция окружений |
| Password file | `--vault-password-file .vault_pass` | Не вводить руками |

### 7.3 Terraform Sensitive + Ephemeral

```hcl
# Ephemeral: не сохраняется в state (Terraform 1.10+)
variable "hcloud_token" {
  type      = string
  sensitive = true
  ephemeral = true
}

# Для CI/CD: передаётся через environment
# export TF_VAR_hcloud_token=$HCLOUD_TOKEN
```

---

## 8. CI/CD интеграция

### 8.1 GitHub Actions Workflow

```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure (IaC)

on:
  push:
    branches: [main]
    paths: ['infra/terraform/**', 'infra/ansible/**']
  pull_request:
    paths: ['infra/terraform/**', 'infra/ansible/**']

env:
  TF_VAR_hcloud_token: ${{ secrets.HCLOUD_TOKEN }}
  TF_VAR_cloudflare_api_token: ${{ secrets.CLOUDFLARE_API_TOKEN }}

jobs:
  terraform-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Terraform Init
        working-directory: infra/terraform/environments/production
        run: terraform init
      - name: Terraform Plan
        working-directory: infra/terraform/environments/production
        run: terraform plan -out=tfplan
      - name: Upload Plan
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infra/terraform/environments/production/tfplan

  terraform-apply:
    needs: terraform-plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Download Plan
        uses: actions/download-artifact@v4
        with: { name: tfplan }
      - name: Terraform Apply
        working-directory: infra/terraform/environments/production
        run: terraform apply -auto-approve tfplan

  ansible-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ansible/ansible-lint-action@v6
        with:
          path: infra/ansible/
```

---

## 9. Тестирование IaC

### 9.1 Terraform Native Tests

```hcl
# infra/terraform/tests/vpn_node_test.tftest.hcl

variables {
  node_name   = "test-node-01"
  location    = "hel1"
  server_type = "cx22"
  ssh_key_ids = []
  node_role   = "remnawave"
  environment = "test"
}

run "vpn_node_creates_successfully" {
  command = plan

  assert {
    condition     = hcloud_server.vpn_node.location == "hel1"
    error_message = "Node must be created in Helsinki"
  }

  assert {
    condition     = hcloud_server.vpn_node.labels["managed_by"] == "terraform"
    error_message = "Node must have managed_by label"
  }
}
```

### 9.2 Molecule для Ansible ролей

```yaml
# infra/ansible/molecule/common/molecule.yml
driver:
  name: docker
platforms:
  - name: test-ubuntu
    image: geerlingguy/docker-ubuntu2404-ansible:latest
    privileged: true
    pre_build_image: true
provisioner:
  name: ansible
verifier:
  name: ansible
```

---

## 10. Day-2 Operations

### 10.1 Операционные сценарии

| Сценарий | Команда |
|---|---|
| Новая нода в Финляндии | `make add-node NODE=fi-02` |
| Обновить все ноды | `make update-nodes` |
| Откат Remnawave | `ansible-playbook rollback-remnawave.yml` |
| Канареечный деплой Helix | `make helix-canary` |
| Ротация Reality-ключей | `ansible-playbook rotate-keys.yml` |
| Аудит безопасности | `ansible-playbook security-audit.yml` |
| Удалить ноду | `terraform destroy -target=module.vpn_nodes["de-02"]` |

---

## 11. Сценарии использования

### 11.1 Сценарий: Добавить VPN-ноду в Токио

```bash
# 1. Добавить в Terraform variables
# infra/terraform/environments/production/terraform.tfvars
vpn_nodes = {
  # ... существующие
  "jp-01" = {
    location    = "tok1"
    server_type = "cx22"
    role        = "remnawave"
  }
}

# 2. Добавить host_vars для Ansible
# infra/ansible/inventory/production/host_vars/jp-01.yml
vault_node_uuid: "xxxxx"
vault_reality_private_key: "yyyyyy"

# 3. Запустить
make deploy
# → Terraform: создаст VPS + DNS
# → Ansible: настроит ОС + Docker + Remnawave Node
```

### 11.2 Сценарий: Обновить Remnawave 2.7.4 → 2.8.0

```bash
# Rolling update: по одной ноде, с health check после каждой
ansible-playbook update-remnawave.yml -e target_version=2.8.0

# Что происходит на каждой ноде:
# 1. docker pull remnawave/node:2.8.0
# 2. docker compose down && up
# 3. Health check (15 попыток × 5 сек)
# 4. Проверка подключения к Panel
# 5. Переход к следующей ноде
```

### 11.3 Сценарий: Канареечный деплой Helix

```bash
# 1. Деплой на 1 ноду (canary)
ansible-playbook helix-canary-deploy.yml --limit helix-canary-01

# 2. Мониторинг 24 часа (Grafana dashboard)

# 3. Раскатка на все Helix-ноды
ansible-playbook update-helix.yml
```

---

## 12. Безопасность

### 12.1 Чеклист безопасности IaC

| # | Правило | Инструмент |
|---|---|---|
| 1 | Секреты НЕ в git (plain-text) | ansible-vault, ephemeral vars |
| 2 | State зашифрован и версионирован | S3 backend + encrypt |
| 3 | API-токены с минимальными правами | Scoped Cloudflare tokens, Hetzner project tokens |
| 4 | SSH: только ключи, без паролей | Ansible role `common` |
| 5 | Firewall: deny по умолчанию | UFW + Hetzner Firewall (двойная защита) |
| 6 | Docker: не от root | USER directive в Dockerfiles |
| 7 | Образы: pin по digest | `image: remnawave/node:2.7.4@sha256:...` |
| 8 | `no_log: true` на секретных задачах | Ansible tasks |
| 9 | PR review обязателен для IaC изменений | GitHub branch protection |
| 10 | `terraform plan` в CI перед apply | GitHub Actions |

### 12.2 Docker и UFW — критический нюанс

> ⚠️ **Docker обходит UFW**, напрямую манипулируя iptables. Решение:

```json
// /etc/docker/daemon.json (деплоится через Ansible)
{
  "iptables": false,
  "default-address-pools": [
    {"base": "172.17.0.0/16", "size": 24}
  ]
}
```

Плюс Hetzner Firewall как **внешний** (облачный) firewall — он работает на уровне гипервизора и не обходится Docker.

---

## 13. Полная структура файлов

```
infra/
├── terraform/
│   ├── environments/
│   │   ├── production/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   ├── backend.tf
│   │   │   ├── versions.tf
│   │   │   └── terraform.tfvars      # 🔐 НЕ в git
│   │   └── staging/
│   │       └── ...
│   ├── modules/
│   │   ├── vpn-node/
│   │   ├── helix-edge/
│   │   ├── dns-record/
│   │   ├── firewall/
│   │   └── control-plane/
│   └── tests/
│       └── *.tftest.hcl
├── ansible/
│   ├── ansible.cfg
│   ├── requirements.yml
│   ├── inventory/
│   │   ├── production/
│   │   │   ├── hosts.yml
│   │   │   ├── group_vars/
│   │   │   │   ├── all.yml
│   │   │   │   ├── vpn_nodes.yml
│   │   │   │   ├── helix_nodes.yml
│   │   │   │   └── vault.yml          # 🔐 ansible-vault encrypted
│   │   │   └── host_vars/
│   │   │       ├── fi-01.yml          # 🔐 Per-node secrets
│   │   │       └── de-01.yml
│   │   └── staging/
│   ├── roles/
│   │   ├── common/                    # SSH, UFW, Fail2ban, sysctl
│   │   ├── docker/                    # Docker CE + Compose plugin
│   │   ├── remnawave-node/            # Remnawave Node deploy
│   │   ├── helix-node/                # Helix Node deploy
│   │   ├── monitoring-agent/          # node-exporter + promtail
│   │   └── backup/                    # Config backup cron
│   ├── playbooks/
│   │   ├── site.yml
│   │   ├── update-remnawave.yml
│   │   ├── update-helix.yml
│   │   ├── rollback-remnawave.yml
│   │   ├── add-node.yml
│   │   ├── rotate-keys.yml
│   │   ├── security-audit.yml
│   │   └── helix-canary-deploy.yml
│   └── molecule/
│       ├── common/
│       └── remnawave-node/
├── Makefile                           # Shortcuts
└── docker-compose.yml                 # Существующий локальный стек
```

---

## 14. Фазы реализации

### Фаза 1 — Фундамент (3-4 дня)

- [ ] Terraform: модули `vpn-node`, `firewall`, `dns-record`
- [ ] Terraform: remote state (S3 backend)
- [ ] Terraform: environments (production + staging)
- [ ] Ansible: роли `common`, `docker`
- [ ] Ansible: vault для секретов
- [ ] Makefile

### Фаза 2 — VPN Provisioning (3-4 дня)

- [ ] Ansible: роль `remnawave-node` (deploy + update)
- [ ] Ansible: роль `monitoring-agent`
- [ ] Playbooks: `site.yml`, `update-remnawave.yml`, `rollback-remnawave.yml`
- [ ] Dynamic inventory (Terraform → Ansible)
- [ ] Тест: привизионить staging-ноду

### Фаза 3 — Helix + Operations (2-3 дня)

- [ ] Terraform: модуль `helix-edge`
- [ ] Ansible: роль `helix-node`
- [ ] Playbooks: `helix-canary-deploy.yml`, `update-helix.yml`
- [ ] Playbook: `rotate-keys.yml`, `security-audit.yml`

### Фаза 4 — CI/CD + Testing (2-3 дня)

- [ ] GitHub Actions: terraform plan/apply
- [ ] GitHub Actions: ansible-lint
- [ ] Terraform native tests (`.tftest.hcl`)
- [ ] Molecule tests для ролей `common`, `remnawave-node`
- [ ] Документация в `docs/plans/`

### Итого: ~10-14 дней

---

## 15. Риски и митигации

| Риск | Вероятность | Митигация |
|---|---|---|
| Terraform state corruption | Низкая | S3 versioning + backup перед каждым apply |
| Lockout при SSH hardening | Средняя | Тестировать на staging, Hetzner Console rescue |
| Docker обходит UFW | Высокая | `"iptables": false` + Hetzner Cloud Firewall |
| Hetzner `datacenter` deprecation (июль 2026) | Определённая | Используем `location` с первого дня |
| Hetzner IP lifecycle changes (май 2026) | Определённая | Provider ≥1.60.0, `auto_delete = false` |
| Утечка секретов в CI/CD логах | Средняя | `no_log: true`, ephemeral vars, masked secrets |
| Rolling update ломает сервис | Средняя | `serial: 1`, health checks, auto-rollback |

---

*Документ подготовлен с учётом best practices Terraform 1.15+, Ansible 11+, Hetzner Cloud API 2026 и текущей архитектуры CyberVPN.*
