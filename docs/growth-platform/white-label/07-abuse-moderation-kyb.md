# Abuse, Moderation, and KYB

## Purpose

White-Label introduces significant abuse risk. This document defines the minimum control system needed before broad public rollout.

## KYB Levels

- `Level 0`: application submitted
- `Level 1`: identity and business basics verified
- `Level 2`: operating business evidence verified
- `Level 3`: strategic or higher-risk partner with deeper review

## Partner Risk Score

Risk score can consider:

- business category
- geography
- brand similarity or impersonation signals
- traffic claims
- payout behavior
- refund behavior
- support burden

## Brand Moderation

Review for:

- trademark or impersonation risk
- misleading claims
- prohibited categories
- unsupported network promises
- unsafe or policy-violating imagery or text

## Bot Creation Limits

Controls:

- limit active bots per workspace;
- limit re-provision attempts;
- require manual review for escalated cases.

## Payout Holds

Payouts may be held for:

- incomplete verification;
- elevated risk;
- refund or fraud anomalies;
- unresolved support or compliance cases.

## Emergency Suspend

The platform must be able to:

- suspend workspace
- suspend bot
- revoke credential
- disable Mini App binding
- stop payouts

## Manual Review

Manual review is required when:

- brand impersonation is suspected;
- managed provisioning repeatedly fails for unclear reasons;
- risk score exceeds threshold;
- payout anomalies appear.

## Blocked Categories

Examples may include:

- impersonation of official institutions;
- disallowed scam or abuse-heavy verticals;
- unsupported or unsafe marketing promises;
- categories blocked by platform policy or legal review.

## Audit Trail

Must log:

- reviewer decisions;
- brand moderation outcomes;
- provisioning actions;
- token rotations;
- suspension events;
- payout holds and releases.

## Admin Tooling Requirements

- searchable review queue
- partner health view
- risk and payout hold indicators
- bot provisioning intervention tools
- emergency suspend actions
