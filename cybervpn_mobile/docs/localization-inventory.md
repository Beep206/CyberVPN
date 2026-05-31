# Mobile Localization Inventory

CyberVPN Mobile separates locale resources from locales that are reviewed and
selectable in the app.

## Active Resource Inventory

`LocaleConfig.supportedLocaleCodes` is the active ARB inventory. It contains 38
locale codes:

`en`, `hi`, `id`, `ru`, `zh`, `ar`, `fa`, `tr`, `vi`, `ur`, `th`, `bn`, `ms`,
`es`, `kk`, `be`, `my`, `uz`, `ha`, `yo`, `ku`, `am`, `fr`, `tk`, `ja`, `ko`,
`he`, `de`, `pt`, `it`, `nl`, `pl`, `fil`, `uk`, `cs`, `ro`, `hu`, `sv`.

`zh_Hant` is outside the active mobile inventory.

## Selectable Locale Policy

`LocaleConfig.selectableLocaleCodes` contains only reviewed locales that can be
shown in the language picker. Current selectable locale:

`en`.

The remaining non-English ARB files are fallback-only resources. They are kept
for future localization work, but they are not user-selectable and their missing
keys do not block release until translation coverage and RTL/manual QA are
approved.

## Coverage Gate

Run the focused gate from `cybervpn_mobile`:

```bash
python3 scripts/check_i18n_coverage.py
```

Expected policy:

- reviewed/selectable locales must have complete coverage against
  `app_en.arb`;
- fallback-only locales are reported with coverage and untranslated counts, but
  missing keys are `SKIP` rather than release-blocking `FAIL`;
- ARB files outside `LocaleConfig.supportedLocaleCodes` fail the gate.
