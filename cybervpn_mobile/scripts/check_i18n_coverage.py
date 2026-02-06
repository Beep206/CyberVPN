#!/usr/bin/env python3
"""Check i18n coverage across all locale ARB files.

Compares each locale's ARB keys against the English (en) baseline and reports:
  - Missing keys per locale
  - Overall coverage percentage per locale
  - Untranslated values (English text copied verbatim to non-English locales)

Exits non-zero if any locale has missing keys.

Usage:
    python scripts/check_i18n_coverage.py [--arb-dir lib/core/l10n/arb]
"""

import json
import sys
from pathlib import Path


def load_arb(path: Path) -> dict[str, str]:
    """Load an ARB file and return only translatable keys (no metadata)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("@") and isinstance(v, str)}


def main() -> int:
    arb_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("lib/core/l10n/arb")

    if not arb_dir.is_dir():
        print(f"ERROR: ARB directory not found: {arb_dir}")
        return 1

    en_path = arb_dir / "app_en.arb"
    if not en_path.exists():
        print(f"ERROR: English baseline not found: {en_path}")
        return 1

    en_keys = load_arb(en_path)
    en_key_set = set(en_keys.keys())
    total_keys = len(en_key_set)

    print(f"Baseline (en): {total_keys} keys\n")

    has_errors = False
    results: list[tuple[str, int, int, int]] = []

    for arb_path in sorted(arb_dir.glob("app_*.arb")):
        if arb_path.name == "app_en.arb":
            continue

        locale = arb_path.stem.replace("app_", "")
        locale_keys = load_arb(arb_path)
        locale_key_set = set(locale_keys.keys())

        missing = en_key_set - locale_key_set
        extra = locale_key_set - en_key_set

        # Detect untranslated values (verbatim English copies).
        # Only flag multi-word values to reduce false positives on
        # proper nouns and technical terms.
        untranslated = 0
        for key in locale_key_set & en_key_set:
            en_val = en_keys[key]
            loc_val = locale_keys[key]
            if en_val == loc_val and " " in en_val and len(en_val) > 10:
                untranslated += 1

        covered = total_keys - len(missing)
        pct = (covered / total_keys * 100) if total_keys > 0 else 100.0

        results.append((locale, covered, len(missing), untranslated))

        if missing:
            has_errors = True

    # Print summary table
    print(f"{'Locale':<12} {'Covered':>8} {'Missing':>8} {'Untranslated':>13} {'Coverage':>9}")
    print("-" * 52)
    for locale, covered, miss, untrans in results:
        pct = covered / total_keys * 100 if total_keys > 0 else 100.0
        status = "OK" if miss == 0 else "FAIL"
        print(f"{locale:<12} {covered:>8} {miss:>8} {untrans:>13} {pct:>8.1f}% {status}")

    print()
    if has_errors:
        print("FAIL: Some locales have missing keys.")
        return 1

    print("OK: All locales have complete key coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
