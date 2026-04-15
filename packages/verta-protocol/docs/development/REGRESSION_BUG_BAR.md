# Regression Bug Bar

`Phase M` uses a strict regression bar.
The project is not allowed to “soak through” severe failures.

## Severity Rules

- `P0`: security break, protocol safety break, unrecoverable control-plane break, or rollback failure. Allowed open count: `0`.
- `P1`: release-blocking transport regression, lifecycle drift that breaks the supported-upstream path, or operator drill failure. Allowed open count: `0`.
- `P2`: important but non-release-blocking defect with a bounded workaround. Allowed open count: explicitly accepted tail only.
- `P3`: low-severity defect or documentation polish. Allowed open count: tracked but not phase-blocking.

## Catastrophic Regression Definition

Any of the following is catastrophic for `Phase M`:

- `Phase I` supported-upstream signoff is no longer `ready`
- WAN staging interop is no longer `ready`
- any canary stage fails its lifecycle, rollback, or Phase L signoff artifact
- rollback proof is missing
- a `P0` or `P1` regression is open

## Accepted Tail

The accepted tail must be explicit in `phase-m-regression-ledger.json`.
If the issue is not listed there, it is not accepted.

For the maintained local `Phase M` close-out, the target accepted tail is `0`.
