# Autonomy Policy v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Green and Amber CyberVPN Paperclip work mergeable without repeated owner intervention while keeping Red production/security actions owner-gated.

**Architecture:** The policy is repository-first and Paperclip-backed: GitLab keeps hard branch and pipeline gates, while Paperclip records reviewer approvals because this GitLab CE instance does not expose required approval rules. The MR template and CI contract validator make the policy visible to every future MR.

**Tech Stack:** GitLab CE, Paperclip AI agents, CODEOWNERS, GitLab MR templates, Python CI contract validator.

---

### Task 1: Add Autonomy Policy v1

**Files:**
- Create: `docs/gitlab/AUTONOMY_POLICY_V1.md`

**Steps:**
1. Define Green, Amber, and Red authority.
2. Define staging and production deploy rules.
3. Define maintainer bot permissions and prohibitions.
4. Define Paperclip task routing.

### Task 2: Wire Policy Into Existing GitLab Docs

**Files:**
- Modify: `docs/gitlab/AI_MR_CONTRACT.md`
- Modify: `docs/gitlab/AI_REVIEW_MAP.md`
- Modify: `.gitlab/merge_request_templates/Default.md`

**Steps:**
1. Link `AUTONOMY_POLICY_V1.md` from the MR contract and review map.
2. Make Green and Amber maintainer-bot merge authority explicit.
3. Keep Red owner or Board approval explicit.
4. Add the Autonomy Policy decision section to the MR template.

### Task 3: Extend The CI Contract Validator

**Files:**
- Modify: `scripts/validate_gitlab_ci_contract.py`

**Steps:**
1. Require the new policy file.
2. Require policy markers in the MR contract, review map, and MR template.
3. Run `python scripts/validate_gitlab_ci_contract.py`.

### Task 4: Publish Through GitLab MR Flow

**Steps:**
1. Create branch `ai/cyba-autonomy/v1-policy`.
2. Open a GitLab MR using the default template.
3. Let CI run.
4. Merge only after the docs-only Green gate passes.

### Task 5: Record Paperclip Evidence

**Steps:**
1. Add a Paperclip evidence comment with the MR URL, pipeline status, and applied GitLab settings.
2. Note that staging auto-deploy is policy-approved but requires a real staging target and staging-only variables before a deploy job is enabled.
