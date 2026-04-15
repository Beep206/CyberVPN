# Unsafe Shortcuts To Avoid

- Do not bypass manifest or token verification behind debug-only silent fallbacks.
- Do not log raw tokens, bootstrap identifiers, refresh credentials, raw HWID, or full manifest bodies.
- Do not trust raw Remnawave JSON directly in bridge policy or manifest compilation.
- Do not keep refresh credentials in plaintext when a hashed or external-reference form is available.
- Do not make the session crate depend directly on Quinn, h3, axum, or Remnawave-specific types.
- Do not accept reserved bits, unknown frozen enums, or malformed frame lengths leniently.
- Do not weaken `iss`, `aud`, `alg`, or `typ` validation for convenience.
- Do not couple gateway policy decisions to user-supplied hints outside verified bridge-issued authority.
