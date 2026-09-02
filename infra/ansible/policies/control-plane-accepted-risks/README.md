# Control-plane accepted-risk decisions

This directory contains explicit, reviewable exceptions for signed container
scan findings. It intentionally contains no active decision by default.

After the image workflow publishes a digest, raw report, report SHA-256 and
signed scan predicate, a repository owner may add one JSON decision that
conforms to `../control-plane-accepted-risk.schema.json`. The decision must
copy the exact image, scanner, Critical/High counts and report digest for every
component with findings. It is also bound to the fixed signer workflow, source
commit and `cybervpn-control-plane-supply-chain/v2` policy.
Keep rationale concise and free of credentials, customer data, private URLs or
raw vulnerability payloads; link only to approved internal tracking metadata.

Promotion accepts a decision only from this protected default-branch directory.
A missing decision, an extra or omitted finding component, a changed digest,
count, report, signer, source commit or policy, and a stale decision for a clean
release all fail closed. The raw report remains a build artifact; the promotion
artifact retains the verification outputs, normalized decision and evidence
hash. Delete obsolete decisions after remediation or a digest change.
