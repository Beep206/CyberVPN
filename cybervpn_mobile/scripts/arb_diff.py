#!/usr/bin/env python3
"""Compare app_en.arb with all other locale ARB files.

Outputs a JSON file with per-locale missing keys and their English values.
Skips @-prefixed metadata keys and @@locale.
"""

import json
import os
import sys

ARB_DIR = os.path.join(os.path.dirname(__file__), '..', 'lib', 'core', 'l10n', 'arb')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'missing_translations.json')


def load_arb(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_translatable_keys(arb: dict) -> set:
    """Return keys that need translation (exclude @-metadata and @@locale)."""
    return {k for k in arb if not k.startswith('@')}


def main():
    en_path = os.path.join(ARB_DIR, 'app_en.arb')
    if not os.path.exists(en_path):
        print(f'Error: {en_path} not found', file=sys.stderr)
        sys.exit(1)

    en_arb = load_arb(en_path)
    en_keys = get_translatable_keys(en_arb)
    print(f'English template: {len(en_keys)} translatable keys')

    result = {}
    total_missing = 0

    for filename in sorted(os.listdir(ARB_DIR)):
        if not filename.endswith('.arb') or filename == 'app_en.arb':
            continue

        locale = filename.replace('app_', '').replace('.arb', '')
        locale_path = os.path.join(ARB_DIR, filename)
        locale_arb = load_arb(locale_path)
        locale_keys = get_translatable_keys(locale_arb)

        missing = en_keys - locale_keys
        if missing:
            result[locale] = {k: en_arb[k] for k in sorted(missing)}
            total_missing += len(missing)
            print(f'  {locale}: {len(missing)} missing keys')
        else:
            print(f'  {locale}: complete')

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'\nTotal: {total_missing} missing translations across {len(result)} locales')
    print(f'Output: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
