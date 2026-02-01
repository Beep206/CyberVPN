# Country Flag Assets

This directory contains SVG country flag icons for the VPN server list.

## Source

Flags sourced from [circle-flags](https://github.com/HatScripts/circle-flags) by HatScripts.
- Project URL: https://hatscripts.github.io/circle-flags/
- Repository: https://github.com/HatScripts/circle-flags

## License

MIT License - Free for commercial and personal use.

## Design

- Format: SVG (scalable vector graphics)
- Style: Minimal circular flags
- Aspect Ratio: 1:1 (circular)
- Optimized: SVGO optimized for small file sizes (<1KB per flag)

## Naming Convention

Flags are named using ISO 3166-1 alpha-2 country codes in lowercase:
- `us.svg` - United States
- `de.svg` - Germany
- `jp.svg` - Japan
- `nl.svg` - Netherlands
- `sg.svg` - Singapore
- `gb.svg` - United Kingdom
- `ca.svg` - Canada
- `au.svg` - Australia
- `br.svg` - Brazil
- `kr.svg` - South Korea
- `in.svg` - India
- `fr.svg` - France
- `ch.svg` - Switzerland
- `se.svg` - Sweden
- `fi.svg` - Finland
- `pl.svg` - Poland
- `ru.svg` - Russia
- `ua.svg` - Ukraine
- `hk.svg` - Hong Kong

## Usage

Access flags via the `FlagAssets` constants class or `FlagWidget` component.

## Updating Flags

To add a new country flag:
1. Download from: `https://hatscripts.github.io/circle-flags/flags/{country-code}.svg`
2. Save to this directory using lowercase ISO 3166-1 alpha-2 code
3. Update `lib/core/constants/flag_assets.dart` with the new country code
4. Run `flutter pub get` to register the asset

## File Size Summary

- Total flags: 19
- Average size: ~400 bytes
- Total directory size: ~80KB
