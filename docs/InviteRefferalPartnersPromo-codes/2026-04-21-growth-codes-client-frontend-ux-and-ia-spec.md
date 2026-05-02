# Growth Codes Client Frontend UX And IA Spec

**Date:** 2026-04-21  
**Status:** target-state customer frontend spec

---

## 1. Goal

The customer frontend must expose growth mechanics clearly without mixing them with partner mechanics.

---

## 2. Core Sections

Recommended customer IA:

1. `Rewards Overview`
2. `Invites`
3. `Referral`
4. `Gift VPN`
5. `Redeem Code`
6. `Wallet Credits`
7. `Checkout Code Input`
8. `Success Page Rewards`
9. `Notifications`

---

## 3. Rewards Overview

Shows:

- active invite count
- referral code summary
- pending rewards
- available credits
- recent activity
- key actions

Actions:

- copy referral link
- view invites
- redeem code
- buy gift

---

## 4. Invites

Shows:

- invite code list
- days granted to friend
- expiry
- status
- share actions
- usage history
- optional conversion reward state

Statuses:

- active
- used
- expired
- revoked

---

## 5. Referral

Shows:

- personal referral code
- referral link
- QR
- friend benefit explanation
- reward table
- invited / registered / paid stats
- pending rewards
- available reward balance
- cap progress

Must not show:

- partner earnings
- payout statements
- partner traffic tools

---

## 6. Gift VPN

Shows:

- plan family selection
- duration selection
- optional recipient message
- gift purchase history
- gift statuses

Statuses:

- created
- sent
- redeemed
- expired
- revoked

---

## 7. Redeem Code

Recommended split:

- checkout code box for promo or referral
- dedicated redeem page for invite or gift

If unified input is used, backend must still decide code type.

---

## 8. Checkout Code UX

Frontend behavior:

- user enters code
- frontend sends quote request
- backend returns accepted effect or conflict
- frontend shows explanation
- if backend returns `wrong_context`, frontend redirects user toward checkout or redeem flow based on backend hint

Frontend must not:

- compute discount
- guess type
- assume stacking

---

## 9. Success Page Hooks

After qualifying purchase:

- show newly issued invites
- show relevant reward explanation
- show share CTA when appropriate

Example:

- `Your annual plan includes 2 invite codes. Share them with friends.`

---

## 10. Notifications

Relevant notification types:

- invite issued
- invite redeemed
- invite expiring soon
- invite expired
- referral reward pending
- referral reward available
- referral reward reversed
- promo accepted or rejected at checkout
- gift purchased
- gift sent
- gift redeemed
- gift expiring soon
- admin-issued gift available

---

## 11. UX Principles

- keep partner mechanics out
- keep reward economics explainable
- separate `discount` from `entitlement`
- separate `gift` from `promo`
- always present backend decision as truth

---

## 12. Launch Recommendation

Launch order:

1. checkout code input
2. invites
3. referral
4. rewards overview
5. gift flows
