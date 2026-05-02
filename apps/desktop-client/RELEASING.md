# Desktop Release

## Standard Windows NSIS Release

Run from `apps/desktop-client`:

```bash
npm run release:win:nsis
```

What it does:

1. Runs release verification:
   - `npm run test`
   - `npm audit --omit=dev`
2. Builds the Windows installer through Tauri:
   - runner: `cargo-xwin`
   - target: `x86_64-pc-windows-msvc`
   - bundle target: `nsis`
3. Generates release artifacts next to the installer:
   - `*.exe`
   - `*.exe.sha256`
   - `*.exe.release.json`
4. Creates a GitHub-ready release bundle:
   - `release-notes.txt`
   - `SHA256SUMS.txt`
   - copied installer/checksum/manifest in one stable folder

## Output Location

Artifacts are written to:

```text
src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis/
```

GitHub-ready bundle is written to:

```text
releases/windows-nsis/<product>_<version>_<arch>/
```

Example files inside the bundle:

- `desktop-client_0.1.5_x64-setup.exe`
- `desktop-client_0.1.5_x64-setup.exe.sha256`
- `desktop-client_0.1.5_x64-setup.exe.release.json`
- `SHA256SUMS.txt`
- `release-notes.txt`

## Useful Environment Overrides

Skip verification:

```bash
DESKTOP_RELEASE_SKIP_VERIFY=1 npm run release:win:nsis
```

Build with a different runner:

```bash
DESKTOP_TAURI_RUNNER=cargo-xwin npm run release:win:nsis
```

Build a different target triple:

```bash
DESKTOP_TAURI_TARGET=aarch64-pc-windows-msvc npm run release:win:nsis
```

Try signing if a Windows signing command is configured:

```bash
DESKTOP_RELEASE_SIGN=1 npm run release:win:nsis
```

## Expected Warnings on Linux / WSL

When building Windows installers from Linux or WSL, these warnings are expected:

- cross-platform compilation is experimental
- installer signing is skipped on non-Windows hosts
- NSIS may print `warning 5202`
- Tauri may warn while patching bundle metadata for updater support on Linux hosts

These do not block the NSIS installer output.
