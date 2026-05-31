#!/usr/bin/env python3
"""Check release-blocking i18n coverage for reviewed mobile locales.

Compares each active locale's ARB keys against the English (en) baseline and
reports:
  - Missing keys per locale
  - Overall coverage percentage per locale
  - Untranslated values (English text copied verbatim to non-English locales)

Only locales listed in LocaleConfig.selectableLocaleCodes are release-blocking.
Other active ARB resources are fallback-only and are reported without failing
the gate until they are reviewed and made selectable.

Usage:
    python scripts/check_i18n_coverage.py [lib/core/l10n/arb]
    python scripts/check_i18n_coverage.py --arb-dir lib/core/l10n/arb
"""

import argparse
import json
import re
import sys
from pathlib import Path

ENGLISH_LOCALE = "en"
DEFAULT_ARB_DIR = Path("lib/core/l10n/arb")
DEFAULT_POLICY_FILE = Path("lib/core/l10n/locale_config.dart")


def load_arb(path: Path) -> dict[str, str]:
    """Load an ARB file and return only translatable keys (no metadata)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("@") and isinstance(v, str)}


def parse_args(argv: list[str]) -> tuple[Path, Path]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "legacy_arb_dir",
        nargs="?",
        help="ARB directory. Kept for compatibility with the old positional CLI.",
    )
    parser.add_argument(
        "--arb-dir",
        dest="arb_dir",
        help="ARB directory to check.",
    )
    parser.add_argument(
        "--policy-file",
        default=str(DEFAULT_POLICY_FILE),
        help="Dart LocaleConfig file containing supported/selectable locale policy.",
    )
    args = parser.parse_args(argv)
    return Path(args.arb_dir or args.legacy_arb_dir or DEFAULT_ARB_DIR), Path(
        args.policy_file
    )


def _extract_dart_string_collection(source: str, name: str) -> list[str]:
    match = re.search(rf"\b{re.escape(name)}\b\s*=\s*(.*?);", source, re.DOTALL)
    if not match:
        raise ValueError(f"Locale policy collection not found: {name}")
    return re.findall(r"'([^']+)'", match.group(1))


def load_locale_policy(policy_file: Path) -> tuple[list[str], set[str]]:
    if not policy_file.exists():
        raise FileNotFoundError(f"Locale policy file not found: {policy_file}")

    source = policy_file.read_text(encoding="utf-8")
    active_locales = _extract_dart_string_collection(source, "supportedLocaleCodes")
    selectable_locales = set(
        _extract_dart_string_collection(source, "selectableLocaleCodes")
    )

    active_set = set(active_locales)
    if len(active_locales) != len(active_set):
        raise ValueError("Locale policy contains duplicate supportedLocaleCodes")
    if ENGLISH_LOCALE not in active_set:
        raise ValueError("English baseline locale must be in supportedLocaleCodes")
    if not selectable_locales:
        raise ValueError("selectableLocaleCodes must contain at least one locale")
    if unknown := sorted(selectable_locales - active_set):
        raise ValueError(
            "selectableLocaleCodes contains locales outside supportedLocaleCodes: "
            + ", ".join(unknown)
        )

    return active_locales, selectable_locales


def check_coverage(arb_dir: Path, policy_file: Path) -> int:
    active_locales, selectable_locales = load_locale_policy(policy_file)
    active_locale_set = set(active_locales)

    if not arb_dir.is_dir():
        print(f"ERROR: ARB directory not found: {arb_dir}")
        return 1

    en_path = arb_dir / f"app_{ENGLISH_LOCALE}.arb"
    if not en_path.exists():
        print(f"ERROR: English baseline not found: {en_path}")
        return 1

    en_keys = load_arb(en_path)
    en_key_set = set(en_keys.keys())
    total_keys = len(en_key_set)

    print(f"Baseline ({ENGLISH_LOCALE}): {total_keys} keys")
    print(f"Active inventory: {len(active_locales)} locales")
    print(
        "Reviewed/selectable release gate: "
        + ", ".join(sorted(selectable_locales))
        + "\n"
    )

    has_errors = False
    results: list[tuple[str, str, int, int, int]] = []

    arb_locales = {
        path.stem.replace("app_", "")
        for path in arb_dir.glob("app_*.arb")
        if path.name != f"app_{ENGLISH_LOCALE}.arb"
    }
    unexpected_locales = sorted(arb_locales - active_locale_set)
    if unexpected_locales:
        print(
            "ERROR: ARB files outside active locale inventory: "
            + ", ".join(unexpected_locales)
        )
        has_errors = True

    for locale in active_locales:
        if locale == ENGLISH_LOCALE:
            continue

        arb_path = arb_dir / f"app_{locale}.arb"
        mode = "reviewed" if locale in selectable_locales else "fallback-only"
        if not arb_path.exists():
            results.append((locale, mode, 0, total_keys, 0))
            print(f"ERROR: Active locale ARB missing: {arb_path}")
            has_errors = True
            continue

        locale_keys = load_arb(arb_path)
        locale_key_set = set(locale_keys.keys())

        missing = en_key_set - locale_key_set

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

        results.append((locale, mode, covered, len(missing), untranslated))

        if mode == "reviewed" and missing:
            has_errors = True

    # Print summary table
    print(
        f"{'Locale':<12} {'Mode':<14} {'Covered':>8} {'Missing':>8} "
        f"{'Untranslated':>13} {'Coverage':>9} {'Gate':>6}"
    )
    print("-" * 80)
    for locale, mode, covered, miss, untrans in results:
        pct = covered / total_keys * 100 if total_keys > 0 else 100.0
        gate = "SKIP" if mode == "fallback-only" else ("OK" if miss == 0 else "FAIL")
        print(
            f"{locale:<12} {mode:<14} {covered:>8} {miss:>8} "
            f"{untrans:>13} {pct:>8.1f}% {gate:>6}"
        )

    print()
    if has_errors:
        print("FAIL: Reviewed locale coverage or active inventory check failed.")
        return 1

    print(
        "OK: Reviewed locale coverage is complete; fallback-only locale gaps are "
        "non-blocking until those locales become selectable."
    )
    return 0


def main() -> int:
    arb_dir, policy_file = parse_args(sys.argv[1:])
    try:
        return check_coverage(arb_dir, policy_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
