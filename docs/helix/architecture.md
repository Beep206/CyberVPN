# Helix Architecture

## Purpose

This document defines the component boundaries and runtime flows for CyberVPN's Helix platform.

## System Context

```mermaid
flowchart LR
    User["Desktop User"] --> Desktop["Desktop Client (Tauri)"]
    Desktop --> Backend["CyberVPN Backend (FastAPI)"]
    Backend --> Adapter["Helix Adapter (Rust/Axum)"]
    Backend --> Remnawave["Remnawave"]
    Adapter --> Remnawave
    Adapter --> DB["PostgreSQL helix schema"]
    Adapter --> Node["Helix Node Daemon"]
    Node --> Runtime["Helix Runtime"]
    Remnawave --> ExistingNodes["Existing Node Estate / Mainstream Transports"]
```

## Authority Boundaries

### Remnawave

Authoritative for:

- users;
- plans and subscriptions;
- billing entitlements;
- node inventory;
- current mainstream transport operations.

### Adapter

Authoritative for:

- Helix manifest issuance;
- Helix node capability registry;
- rollout state and channels;
- manifest and assignment version metadata;
- transport-specific health aggregation.

### Backend

Authoritative public facade for:

- authenticated desktop manifest resolution;
- capability retrieval;
- authenticated admin visibility and rollout actions.

### Node Daemon

Authoritative only for:

- local bundle application state;
- local last-known-good reference;
- local runtime health observation.

## Desktop Manifest Flow

```mermaid
sequenceDiagram
    participant Desktop as Desktop Client
    participant Backend as FastAPI Backend
    participant Remnawave as Remnawave
    participant Adapter as PT Adapter

    Desktop->>Backend: Authenticated manifest request + client capabilities
    Backend->>Remnawave: Read entitlement and inventory context
    Backend->>Adapter: Internal resolve-manifest request
    Adapter-->>Backend: Signed manifest + rollout metadata + compatible profile selection
    Backend-->>Desktop: Desktop manifest response
    Desktop->>Desktop: Verify compatibility, profile family, and signature
    Desktop->>Desktop: Start sidecar or recover to stable core
```

## Protocol Agility Control Loop

```mermaid
sequenceDiagram
    participant SRE as SRE / Ops
    participant Adapter as PT Adapter
    participant Backend as FastAPI Backend
    participant Desktop as Desktop Runtime
    participant Node as Node Daemon

    SRE->>Adapter: Promote or revoke transport profile policy
    Adapter->>Backend: Expose updated manifest semantics
    Backend->>Desktop: Deliver compatible manifest
    Adapter->>Node: Deliver compatible assignment
    Desktop->>Desktop: Accept profile or fall back safely
    Node->>Node: Apply candidate profile or restore last-known-good
```

## Node Assignment Flow

```mermaid
sequenceDiagram
    participant Node as Node Daemon
    participant Adapter as PT Adapter
    participant DB as PT Schema
    participant Runtime as Node Runtime

    Node->>Adapter: Authenticated assignment check
    Adapter->>DB: Fetch rollout state and node assignment
    Adapter-->>Node: Versioned node-assignment bundle
    Node->>Node: Persist pending bundle atomically
    Node->>Runtime: Apply new bundle
    Node->>Node: Run health gate
    alt Health gate passes
        Node->>Node: Mark active bundle
    else Health gate fails
        Node->>Node: Restore last-known-good bundle
    end
    Node-->>Adapter: Node heartbeat with bundle status
```

## Data Ownership Rules

- No transport-specific rollout or manifest state is stored in `Remnawave` tables.
- Remnawave `Node Plugins` can be used only for narrow node-local helpers; Helix ownership does not move into plugin code.
- Adapter-owned state lives under the `helix` schema.
- Desktop stores only what is required for runtime operation, health, and recovery.
- Node daemon stores only local operational state needed for bundle application and rollback.

## Failure and Recovery Model

- Adapter manifest revoke must stop new assignments quickly.
- Adapter profile rotation must prefer compatible profile changes before binary replacement.
- Node daemon must restore last-known-good on failed health gate.
- Desktop must restore a stable core when private runtime startup or health fails.
- Baseline transport operations must remain isolated from Helix failure domains.
