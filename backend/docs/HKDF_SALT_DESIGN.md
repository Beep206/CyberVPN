# HKDF Salt Design Decision (LOW-001)

## Overview

This document describes the design decision for HKDF (HMAC-based Key Derivation Function) salt usage in the CyberVPN backend, specifically for TOTP secret encryption.

## Current Implementation

The TOTP encryption service uses HKDF for key derivation:

```python
# src/infrastructure/totp/totp_encryption.py
import hashlib
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def _derive_key(master_key: str) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,  # Uses zero-length salt (HKDF default)
        info=b"totp-encryption",
    )
    return hkdf.derive(master_key.encode())
```

## Design Decision: No Salt

**Decision**: Use `salt=None` (zero-length salt) for HKDF key derivation.

**Rationale**:

1. **Single Master Key**: The TOTP encryption uses a single, long-lived master key (`TOTP_ENCRYPTION_KEY`). There is no need to derive multiple keys from the same master.

2. **Key Quality**: The master key is expected to be a cryptographically random 32+ byte value (generated via `secrets.token_urlsafe(32)`). HKDF with no salt is appropriate when the input key material already has high entropy.

3. **Deterministic Derivation**: Without salt, the derived key is deterministic. This is intentional - all instances of the service derive the same encryption key from the same master key.

4. **RFC 5869 Compliance**: Per RFC 5869 Section 3.1, a zero-length salt is acceptable when the input key material is already uniformly random.

## Security Considerations

### Why This Is Acceptable

- The master key is generated from a CSPRNG (`secrets.token_urlsafe`)
- The `info` parameter provides domain separation ("totp-encryption")
- Key rotation is achieved by rotating the master key itself

### When Salt Would Be Required

Salt would be necessary if:
- Deriving multiple keys from the same master key
- Master key has low entropy (e.g., password-based)
- Need to prevent precomputation attacks

## Future Enhancement (Optional)

If multi-tenant or multi-purpose key derivation is needed in the future:

```python
def _derive_key_with_salt(master_key: str, purpose: str, tenant_id: str | None = None) -> bytes:
    salt = (tenant_id or "default").encode()
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=purpose.encode(),
    )
    return hkdf.derive(master_key.encode())
```

## References

- [RFC 5869 - HMAC-based Extract-and-Expand Key Derivation Function](https://tools.ietf.org/html/rfc5869)
- [NIST SP 800-56C - Key Derivation](https://csrc.nist.gov/publications/detail/sp/800-56c/rev-2/final)
