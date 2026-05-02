# Growth Codes Risk, Anti-Abuse, And Compliance Spec

**Date:** 2026-04-21  
**Status:** target-state safety baseline

---

## 1. Goal

Protect growth mechanics from:

- self-referral
- invite farming
- promo brute force
- gift abuse
- deceptive disclosure behavior

---

## 2. Risk Decision Model

Suggested risk decisions:

- `allowed`
- `allowed_with_hold`
- `blocked`
- `requires_manual_review`
- `reversed_after_review`

These decisions may apply to:

- code resolution
- code redemption
- reward release
- admin-issued grants

---

## 3. Referral Abuse Checks

Check for:

- same risk subject
- same email cluster
- same device cluster
- same IP cluster
- same funding source
- circular referrals
- abnormal reward velocity

---

## 4. Invite Abuse Checks

Check for:

- self invite
- multiple free-access cycles by same subject
- invite farming across device or household clusters
- repeated redemptions by same subject

---

## 5. Promo Abuse Checks

Check for:

- brute-force attempts
- leaked private promo
- geo misuse
- abnormal refund rate by promo
- per-user overuse

---

## 6. Gift Abuse Checks

Check for:

- bulk buy then refund patterns
- repeated redemption across same risk cluster
- laundering through unauthorized resale
- stolen-payment gift purchase patterns

---

## 7. Velocity And Rate Rules

Risk policy should explicitly define:

- resolution attempt rate limits
- brute-force thresholds
- code-entry velocity by IP, session and user
- repeated invalid code thresholds
- suspicious cluster escalation rules

---

## 8. Reward Blocking States

Rewards may be:

- pending
- available
- blocked_by_risk
- reversed
- expired

---

## 9. Automatic And Manual Review

The platform must distinguish:

- automatic decision
- manual review required
- manual override

Ownership should be explicit:

- fraud or risk queue
- support queue
- growth operations queue

---

## 10. Review Queues

Admin queues should exist for:

- referral abuse review
- invite abuse review
- promo leakage review
- gift abuse review
- brute-force review
- suspicious cluster review

---

## 11. Allowlist And Blocklist

Where policy requires it, risk layer should support:

- allowlist
- blocklist
- temporary hold
- permanent denial

These controls must be auditable.

---

## 12. Compliance Notes

Required policy outcomes:

- no rewards for fake reviews
- no incentive tied to deceptive review behavior
- creator or influencer promo usage must carry disclosure when material benefit exists
- partner-facing campaign assets must include approved disclosure text

---

## 13. Audit Requirements

Risk decisions must record:

- actor
- reason
- signals used
- affected code or relationship
- timestamp

Evidence retention should preserve:

- decision summary
- reason code
- linked lifecycle object

---

## 14. Default Enforcement Rule

When abuse confidence is high:

- block reward first
- preserve audit trail
- avoid destructive silent cleanup
