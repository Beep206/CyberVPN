from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_FILES = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "releases"
    / "task1-task2-20260712"
    / "final-main-production-audit-20260712.md",
    REPO_ROOT
    / "docs"
    / "architecture"
    / "CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md",
)
FORBIDDEN_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "subscription_token_path": re.compile(r"/api/sub/[A-Za-z0-9_-]{8,}"),
    "uuid": re.compile(
        r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.IGNORECASE
    ),
    "private_key": re.compile(r"BEGIN (?:RSA |OPENSSH )?PRIVATE KEY"),
    "bearer": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}", re.IGNORECASE),
    "vless_url": re.compile(r"vless://", re.IGNORECASE),
}
MARKDOWN_LINK_RE = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def main() -> None:
    failures: list[str] = []
    for path in EVIDENCE_FILES:
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        for name, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                failures.append(f"{relative_path}: forbidden pattern {name}")
        if text.count("```") % 2:
            failures.append(f"{relative_path}: unbalanced code fences")
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or raw_target.startswith("#"):
                continue
            if not (path.parent / target).resolve().exists():
                failures.append(f"{relative_path}: missing relative link {target}")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"remnawave_tz_evidence=pass files={len(EVIDENCE_FILES)}")


if __name__ == "__main__":
    main()
