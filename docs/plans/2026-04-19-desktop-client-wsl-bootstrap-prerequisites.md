# Desktop Client WSL Bootstrap Prerequisites

**Date:** 2026-04-19  
**Status:** validated local bootstrap note  
**Scope:** `apps/desktop-client` local Rust validation in Ubuntu WSL

---

## 1. Purpose

This note centralizes the Linux / WSL system prerequisites required to run local Rust validation for the desktop client.

It exists because local desktop validation previously failed in WSL during `cargo check`, even though the desktop frontend build itself already worked. The missing details were not previously captured in a single bootstrap note.

---

## 2. Validated Environment

This bootstrap was validated in:

- Ubuntu `24.04.3 LTS` under WSL
- `rustc 1.94.1`
- `cargo 1.94.1`

Validation command:

```bash
cd apps/desktop-client/src-tauri
cargo check
```

Result on 2026-04-19:

- `cargo check` completed successfully
- the earlier `webkit2gtk / libsoup / javascriptcoregtk` blocker no longer reproduced

---

## 3. Official Reference

Primary upstream reference:

- Tauri prerequisites for Linux / Debian / Ubuntu: https://v2.tauri.app/start/prerequisites/

That page documents the standard Debian/Ubuntu dependency family for Tauri Linux development. In this repository's WSL environment, the Rust build also needed explicit confirmation of the `libsoup-3.0` and `javascriptcoregtk-4.1` development packages used by the underlying GTK/WebKit stack.

---

## 4. Required Packages

For a reproducible Ubuntu / WSL bootstrap in this repository, install:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  curl \
  wget \
  file \
  pkg-config \
  libssl-dev \
  libayatana-appindicator3-dev \
  libwebkit2gtk-4.1-dev \
  libsoup-3.0-dev \
  libjavascriptcoregtk-4.1-dev \
  libxdo-dev \
  librsvg2-dev
```

Notes:

- This command is intentionally explicit rather than minimal. It keeps the desktop bootstrap reproducible in WSL instead of relying on transitive package resolution.
- `libsoup-3.0-dev` and `libjavascriptcoregtk-4.1-dev` are the packages that mattered for the previously failing local Rust validation.

---

## 5. Failure Signature This Resolves

Before this bootstrap, `cargo check` in `apps/desktop-client/src-tauri` failed while compiling GTK/WebKit-related crates:

- `soup3-sys`
- `javascriptcore-rs-sys`
- `webkit2gtk-sys`

The missing system libraries surfaced as:

- `libsoup-3.0`
- `javascriptcoregtk-4.1`
- `webkit2gtk-4.1`

This note exists so the failure no longer has to be rediscovered from raw Cargo logs.

---

## 6. Verification Flow

Run:

```bash
cd apps/desktop-client/src-tauri
cargo check
```

Optional follow-up:

```bash
cargo report future-incompatibilities --id 1
```

Current non-blocking note from the validated run:

- `xcap v0.0.12` reports a future incompatibility warning related to never-type fallback
- this does **not** block current local validation
- it should be treated as later dependency hygiene, not as a failure of WSL bootstrap

---

## 7. Closure Meaning

This note closes the old residual that said desktop local Rust validation was blocked in WSL by missing system packages.

What is now true:

- the prerequisite package set is explicit
- the bootstrap command is reproducible
- local `cargo check` succeeds in the validated WSL environment

What this note does **not** claim:

- that every desktop TypeScript or UI issue is closed
- that desktop release packaging was revalidated end-to-end in this step
- that all future-incompatibility warnings in transitive Rust crates are resolved
