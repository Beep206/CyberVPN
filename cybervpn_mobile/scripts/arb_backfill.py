#!/usr/bin/env python3
"""Backfill missing ARB keys from app_en.arb into all locale files.

For each missing key, copies the English value with an [EN] prefix
to mark it as untranslated. This ensures flutter gen-l10n passes
without 'untranslated message(s)' warnings.

Usage:
    python3 scripts/arb_backfill.py           # Dry run (show what would change)
    python3 scripts/arb_backfill.py --apply   # Apply changes to ARB files
"""

import json
import os
import sys

ARB_DIR = os.path.join(os.path.dirname(__file__), '..', 'lib', 'core', 'l10n', 'arb')


def load_arb(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_arb(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def get_translatable_keys(arb: dict) -> set:
    """Return keys that need translation (exclude @-metadata and @@locale)."""
    return {k for k in arb if not k.startswith('@')}


def prefix_value(value: str) -> str:
    """Add [EN] prefix to mark as untranslated."""
    if isinstance(value, str):
        return f'[EN] {value}'
    return value


def main():
    apply = '--apply' in sys.argv

    en_path = os.path.join(ARB_DIR, 'app_en.arb')
    if not os.path.exists(en_path):
        print(f'Error: {en_path} not found', file=sys.stderr)
        sys.exit(1)

    en_arb = load_arb(en_path)
    en_keys = get_translatable_keys(en_arb)
    print(f'English template: {len(en_keys)} translatable keys')
    print(f'Mode: {"APPLY" if apply else "DRY RUN (use --apply to write)"}')
    print()

    total_added = 0

    for filename in sorted(os.listdir(ARB_DIR)):
        if not filename.endswith('.arb') or filename == 'app_en.arb':
            continue

        locale = filename.replace('app_', '').replace('.arb', '')
        locale_path = os.path.join(ARB_DIR, filename)
        locale_arb = load_arb(locale_path)
        locale_keys = get_translatable_keys(locale_arb)

        missing = en_keys - locale_keys
        if not missing:
            print(f'  {locale}: complete (no missing keys)')
            continue

        print(f'  {locale}: adding {len(missing)} keys')
        total_added += len(missing)

        if apply:
            for key in sorted(missing):
                en_value = en_arb[key]
                locale_arb[key] = prefix_value(en_value)

                # Copy metadata (@key) if it exists
                meta_key = f'@{key}'
                if meta_key in en_arb and meta_key not in locale_arb:
                    locale_arb[meta_key] = en_arb[meta_key]

            save_arb(locale_path, locale_arb)

    print(f'\nTotal: {total_added} keys {"added" if apply else "would be added"}')
    if not apply and total_added > 0:
        print('Run with --apply to write changes.')


if __name__ == '__main__':
    main()
