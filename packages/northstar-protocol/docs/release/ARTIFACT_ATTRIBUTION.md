# Artifact Attribution

Northstar `Phase N` does not invent a new artifact format.
It closes the release using already accepted machine-readable summaries and one final git-attributed signoff record.

## Attributable Inputs

- accepted phase summaries under `target/northstar/`
- maintained workflow definitions under `.github/workflows/`
- maintained release docs under `docs/release/`
- one final `Phase N` summary at `target/northstar/phase-n-production-ready-signoff-summary.json`

## Attribution Rules

- release closure must name the git branch used for the decision
- release closure must name the exact commit SHA used for the decision
- the signoff worktree must be clean so the decision maps to unambiguous source
- the final summary must point back to the exact phase evidence it consumed

## What This Does Not Claim

- It does not claim a different protocol version or a widened carrier set.
- It does not claim a wider Remnawave integration boundary than the maintained non-fork path.
- It does not hide accepted limitations; those stay explicit in `KNOWN_LIMITATIONS.md`.
