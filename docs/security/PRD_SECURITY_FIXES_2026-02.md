# FastAPI Backend Security Remediation - Product Requirements Document

**Document Version:** 1.0
**Created:** 2026-02-06
**Target Completion:** 2026-02-20 (1 sprint)
**Priority:** High
**Clarification Rounds:** 2
**Quality Score:** 94/100

---

## 1. Executive Summary

### Problem Statement

A security audit of the CyberVPN FastAPI backend identified **4 vulnerable dependencies** with known CVEs and **1 static analysis finding** (Bandit B104). These vulnerabilities expose the application to potential denial-of-service attacks, timing attacks, and information disclosure. Left unaddressed, they create compliance risks and potential attack vectors for privacy-conscious users relying on CyberVPN infrastructure.

### Why Now

- **CVE-2026-1703** (pip) and **CVE-2026-0994** (protobuf) are newly disclosed vulnerabilities requiring immediate attention
- **CVE-2024-23342** (ecdsa) is an older unpatched vulnerability in a library with no planned fix
- The `py` package is deprecated and actively flagged by security scanners
- Establishing `pip-audit` in CI prevents future accumulation of vulnerable dependencies

### Proposed Solution

1. Update vulnerable dependencies to patched versions
2. Replace or remove unmaintainable libraries (`ecdsa`, `py`)
3. Fix hardcoded `0.0.0.0` default in audit logging code
4. Integrate `pip-audit` into CI pipeline for continuous monitoring

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| CVE Count | 0 | `pip-audit` returns no findings |
| Bandit Findings | 0 medium+ | `bandit -r src/` clean |
| Test Suite | 100% pass | `pytest` exit code 0 |
| CI Pipeline | Automated | `pip-audit` runs on every PR |
| Deployment | Verified | Staging environment validated |

---

## 2. User Experience and Functionality

### User Personas

| Persona | Description | Impact |
|---------|-------------|--------|
| **DevOps Engineer** | Deploys and maintains backend infrastructure | Primary executor of remediation |
| **Security Team** | Reviews and approves security changes | Signs off on completion |
| **Backend Developer** | Writes and tests application code | May need to update code using affected libraries |
| **End User** | VPN customer | Indirect beneficiary (improved security posture) |

### User Stories

#### US-1: Dependency Update Execution
**As a** DevOps Engineer
**I want to** update vulnerable dependencies to secure versions
**So that** the application is protected from known exploits

**Acceptance Criteria:**
- [ ] `pip` updated to version >= 26.0
- [ ] `protobuf` updated to version >= 6.33.5
- [ ] `ecdsa` replaced with `cryptography` library (pyca/cryptography)
- [ ] `py` package removed or pinned to safe version (if direct dependency)
- [ ] All existing tests pass after updates
- [ ] No new deprecation warnings introduced

#### US-2: Code Remediation
**As a** Backend Developer
**I want to** fix the hardcoded bind address in audit_log_repo.py
**So that** Bandit scans pass without medium-severity findings

**Acceptance Criteria:**
- [ ] Default `ip_address` parameter changed from `"0.0.0.0"` to `None`
- [ ] Calling code updated to explicitly pass IP address
- [ ] Bandit scan returns no B104 findings
- [ ] Audit log functionality verified in staging

#### US-3: CI/CD Integration
**As a** Security Team member
**I want to** have automated vulnerability scanning in CI
**So that** future vulnerabilities are caught before deployment

**Acceptance Criteria:**
- [ ] `pip-audit` added to CI workflow
- [ ] Pipeline fails on any CVE with severity >= MEDIUM
- [ ] Audit results visible in PR checks
- [ ] Documentation updated with new CI step

### Non-Goals (Out of Scope)

- Upgrading Python version (already on 3.13+)
- Full security penetration testing
- Refactoring unrelated code
- Adding new features to audit logging
- Addressing low-severity Bandit findings

---

## 3. Technical Specifications

### 3.1 Vulnerability Inventory

| ID | Package | Current Version | CVE/Advisory | Severity | Target Version | Action |
|----|---------|-----------------|--------------|----------|----------------|--------|
| V1 | pip | 25.3 | CVE-2026-1703 | High | >= 26.0 | Update |
| V2 | protobuf | 5.29.5 | CVE-2026-0994 | High | >= 6.33.5 | Update |
| V3 | ecdsa | 0.19.1 | CVE-2024-23342 | Medium | N/A (no fix) | Replace |
| V4 | py | 1.11.0 | PYSEC-2022-42969 | Medium | Remove | Remove/Replace |
| B1 | audit_log_repo.py | Line 21 | Bandit B104 | Medium | N/A | Code fix |

### 3.2 Remediation Details

#### V1: pip Update (CVE-2026-1703)

**Current State:** pip 25.3 installed in build environment
**Target State:** pip >= 26.0

**Implementation:**
```dockerfile
# In Dockerfile
RUN pip install --upgrade pip>=26.0
```

**Verification:**
```bash
pip --version  # Must show >= 26.0
pip-audit      # Must not report CVE-2026-1703
```

#### V2: protobuf Update (CVE-2026-0994)

**Current State:** protobuf 5.29.5 (transitive dependency)
**Target State:** protobuf >= 6.33.5

**Implementation:**
```toml
# In pyproject.toml [project] dependencies or constraints
"protobuf>=6.33.5"
```

**Verification:**
```bash
pip show protobuf  # Must show >= 6.33.5
pip-audit          # Must not report CVE-2026-0994
```

**Risk:** Major version bump (5.x to 6.x) may have breaking changes. Review protobuf usage and test thoroughly.

#### V3: ecdsa Replacement (CVE-2024-23342)

**Current State:** ecdsa 0.19.1 vulnerable to Minerva timing attack
**Target State:** Remove ecdsa, use `cryptography` library instead

**Background:** The ecdsa library maintainers have explicitly stated they will not fix CVE-2024-23342 because "Implementing side-channel-free code in pure Python is impossible." They recommend using `pyca/cryptography` as a secure alternative.

**Implementation:**
1. Identify all code importing `ecdsa`
2. Replace with equivalent `cryptography` APIs:
   ```python
   # Before (ecdsa)
   from ecdsa import SigningKey, SECP256k1
   sk = SigningKey.generate(curve=SECP256k1)

   # After (cryptography)
   from cryptography.hazmat.primitives.asymmetric import ec
   from cryptography.hazmat.backends import default_backend
   private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
   ```
3. Remove `ecdsa` from dependencies
4. Add `cryptography` if not already present (likely already via PyJWT[crypto])

**Verification:**
```bash
pip show ecdsa     # Should return "not found"
pip-audit          # Must not report CVE-2024-23342
pytest             # All crypto-related tests pass
```

#### V4: py Package Removal (PYSEC-2022-42969)

**Current State:** py 1.11.0 (likely transitive via older pytest)
**Target State:** Package removed from dependency tree

**Background:** The `py` library is deprecated and has a known ReDoS vulnerability. Modern pytest versions (7.2+) no longer depend on it.

**Implementation:**
1. Check if `py` is a direct dependency:
   ```bash
   pip show py | grep -i "required-by"
   ```
2. If transitive only (from pytest):
   - Update pytest to latest version (>= 8.0)
   - Verify `py` is no longer installed
3. If direct dependency exists in codebase:
   - Audit usage and replace with standard library equivalents
   - `py.path.local` -> `pathlib.Path`

**Verification:**
```bash
pip show py        # Should return "not found"
pip-audit          # Must not report PYSEC-2022-42969
```

#### B1: Hardcoded Bind Address Fix (Bandit B104)

**Current State:** File `src/infrastructure/database/repositories/audit_log_repo.py` line 21
```python
ip_address: str = "0.0.0.0",
```

**Target State:** No hardcoded bind-all address
```python
ip_address: str | None = None,
```

**Implementation:**
1. Change default parameter value from `"0.0.0.0"` to `None`
2. Update all call sites to explicitly provide IP address from request context
3. Handle `None` case in audit log storage (store as NULL or "unknown")

**Affected Files:**
- `/home/beep/projects/VPNBussiness/backend/src/infrastructure/database/repositories/audit_log_repo.py`
- Callers in `registration.py`, `routes.py` (review for explicit IP passing)

**Verification:**
```bash
bandit -r src/ -ll  # No B104 findings
pytest              # Audit log tests pass
```

### 3.3 Architecture Impact

```
[CI Pipeline]
     |
     v
[pip-audit] --> FAIL on CVE --> Block merge
     |
     v (pass)
[pytest] --> [Build] --> [Staging Deploy]
     |
     v
[Verification] --> [Production Deploy]
```

**No architectural changes required.** This is a dependency update and minor code fix with no impact on system design.

### 3.4 Integration Points

| System | Impact | Action Required |
|--------|--------|-----------------|
| CI/CD Pipeline | New step | Add pip-audit job |
| Docker Build | Updated base | Ensure pip upgrade in Dockerfile |
| pyproject.toml | Version constraints | Add/update dependency versions |
| Staging Environment | Validation | Deploy and test before production |

### 3.5 Security and Privacy

- **No new data handling** introduced
- **Improved security posture** by removing vulnerable code paths
- **Audit logging** continues to function with explicit IP handling
- **Backward compatibility** maintained for API contracts

---

## 4. Risks and Mitigations

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| protobuf 6.x breaking changes | Medium | High | Review changelog, run full test suite, manual QA in staging |
| ecdsa removal breaks functionality | Low | High | Audit all usages before removal, create migration path |
| pytest update breaks test suite | Low | Medium | Pin to tested version, run full suite before merge |
| CI pipeline slowdown | Low | Low | Cache pip-audit database, run in parallel with tests |

### Rollback Strategy

1. **Git revert** - All changes in single PR, easy to revert
2. **Dependency pinning** - Keep old versions in git history
3. **Staging validation** - Full test before production
4. **Feature flags** - Not applicable (infrastructure changes)

### Dependency Risks

| Dependency | Risk | Alternative |
|------------|------|-------------|
| ecdsa | No upstream fix ever | cryptography (recommended by ecdsa maintainers) |
| protobuf | Major version jump | Test thoroughly; no alternative for gRPC compatibility |
| py | Deprecated, unmaintained | Remove entirely; use pathlib |

---

## 5. Execution Phases

### Phase 1: Assessment and Preparation (Days 1-2)

**Goal:** Confirm findings, prepare environment, identify all affected code

- [ ] Run `pip-audit` to confirm current vulnerability state
- [ ] Run `bandit -r src/ -ll` to confirm static analysis findings
- [ ] Audit codebase for `ecdsa` imports and usage
- [ ] Audit codebase for `py` imports and usage
- [ ] Review protobuf 6.x migration guide
- [ ] Create feature branch `security/cve-remediation-2026-02`

**Deliverables:** Audit report, migration plan document
**Time:** 2 days

### Phase 2: Dependency Updates (Days 3-5)

**Goal:** Update all vulnerable dependencies

- [ ] Update pip in Dockerfile to >= 26.0
- [ ] Add protobuf >= 6.33.5 constraint to pyproject.toml
- [ ] Replace ecdsa with cryptography APIs
- [ ] Update pytest and remove py package
- [ ] Run test suite, fix any failures
- [ ] Update lockfile / dependency resolution

**Deliverables:** Updated pyproject.toml, Dockerfile, code changes
**Time:** 3 days

### Phase 3: Code Remediation (Day 6)

**Goal:** Fix static analysis finding

- [ ] Modify `audit_log_repo.py` line 21 default parameter
- [ ] Update all call sites to pass explicit IP address
- [ ] Add/update unit tests for audit logging
- [ ] Run Bandit scan to verify fix

**Deliverables:** Code changes, updated tests
**Time:** 1 day

### Phase 4: CI Integration (Day 7)

**Goal:** Add automated vulnerability scanning

- [ ] Add `pip-audit` step to CI workflow
- [ ] Configure failure threshold (MEDIUM and above)
- [ ] Add caching for pip-audit database
- [ ] Document new CI step in developer guide

**Deliverables:** CI configuration, documentation
**Time:** 1 day

### Phase 5: Testing and Validation (Days 8-9)

**Goal:** Comprehensive validation before production

- [ ] Full pytest suite (unit + integration)
- [ ] Deploy to staging environment (docker-compose)
- [ ] Manual verification of audit logging
- [ ] Verify all CVEs resolved (`pip-audit` clean)
- [ ] Verify Bandit scan clean
- [ ] Security team sign-off

**Deliverables:** Test reports, staging validation
**Time:** 2 days

### Phase 6: Production Deployment (Day 10)

**Goal:** Ship to production

- [ ] Merge PR to main
- [ ] Deploy to production
- [ ] Monitor logs for errors
- [ ] Final `pip-audit` verification in production
- [ ] Close security tickets/issues

**Deliverables:** Production deployment, closure report
**Time:** 1 day

---

## 6. Acceptance Criteria Summary

### Functional Acceptance

- [ ] `pip-audit` returns 0 vulnerabilities
- [ ] `bandit -r src/ -ll` returns 0 findings
- [ ] All pytest tests pass (100%)
- [ ] Audit logging functions correctly with explicit IP addresses
- [ ] No `ecdsa` package in dependency tree
- [ ] No `py` package in dependency tree
- [ ] `pip` version >= 26.0
- [ ] `protobuf` version >= 6.33.5

### Quality Standards

- [ ] Code review approved by 2 engineers
- [ ] Security team sign-off obtained
- [ ] CI pipeline includes `pip-audit` check
- [ ] No regressions in existing functionality
- [ ] Staging environment validated

### Documentation

- [ ] CHANGELOG updated with security fixes
- [ ] CI documentation updated with pip-audit step
- [ ] Any API changes documented (if applicable)

---

## Appendix A: Reference Links

- [CVE-2024-23342 - ecdsa Minerva Attack](https://nvd.nist.gov/vuln/detail/cve-2024-23342)
- [ecdsa Security Policy (No Fix Planned)](https://security.snyk.io/vuln/SNYK-PYTHON-ECDSA-6184115)
- [pyca/cryptography (Recommended Alternative)](https://cryptography.io/)
- [PYSEC-2022-42969 - py ReDoS](https://github.com/pytest-dev/pytest/issues/10392)
- [pip-audit GitHub](https://github.com/pypa/pip-audit)
- [Bandit B104 Documentation](https://bandit.readthedocs.io/en/latest/plugins/b104_hardcoded_bind_all_interfaces.html)

## Appendix B: Affected Files

| File | Change Type |
|------|-------------|
| `pyproject.toml` | Dependency versions |
| `Dockerfile` | pip upgrade |
| `src/infrastructure/database/repositories/audit_log_repo.py` | Parameter default |
| `.github/workflows/*.yml` (or CI config) | pip-audit step |
| Files importing `ecdsa` | Library replacement |

---

**Document Status:** Ready for Implementation
**Next Action:** Create feature branch and begin Phase 1
