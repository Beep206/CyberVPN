# Font Assets for Offline Support

This directory is for **optional** offline font bundling. By default, the `google_fonts` package automatically downloads and caches fonts from Google Fonts servers.

## When to Bundle Fonts Offline

Bundle fonts here if you need:
- Guaranteed offline availability without network dependency
- Reduced first-load latency
- Compliance requirements to avoid external CDN usage
- App store submission with self-contained assets

## How to Bundle Fonts Offline

### 1. Download Font Files

Download Orbitron and JetBrains Mono font files (.ttf) from Google Fonts:
- Orbitron: https://fonts.google.com/specimen/Orbitron
- JetBrains Mono: https://fonts.google.com/specimen/JetBrains+Mono

Place the `.ttf` files in this directory:
```
assets/fonts/
  Orbitron-Regular.ttf
  Orbitron-Medium.ttf
  Orbitron-Bold.ttf
  JetBrainsMono-Regular.ttf
  JetBrainsMono-Medium.ttf
  JetBrainsMono-Bold.ttf
```

### 2. Register Fonts in pubspec.yaml

Uncomment and configure the fonts section in `pubspec.yaml`:

```yaml
flutter:
  fonts:
    - family: Orbitron
      fonts:
        - asset: assets/fonts/Orbitron-Regular.ttf
          weight: 400
        - asset: assets/fonts/Orbitron-Medium.ttf
          weight: 500
        - asset: assets/fonts/Orbitron-Bold.ttf
          weight: 700

    - family: JetBrainsMono
      fonts:
        - asset: assets/fonts/JetBrainsMono-Regular.ttf
          weight: 400
        - asset: assets/fonts/JetBrainsMono-Medium.ttf
          weight: 500
        - asset: assets/fonts/JetBrainsMono-Bold.ttf
          weight: 700
```

### 3. No Code Changes Required

The `google_fonts` package automatically uses bundled fonts as a fallback when network is unavailable or if you explicitly configure it.

## Current Implementation

Currently, fonts are **not bundled offline**. The app uses the default behavior of `google_fonts`:
- Downloads fonts on first use
- Caches fonts locally after download
- Works offline after initial download

This provides a good balance of app size and functionality for most use cases.

## License

When bundling fonts, ensure compliance with font licenses:
- Orbitron: SIL Open Font License 1.1
- JetBrains Mono: SIL Open Font License 1.1

Both fonts are free to use and distribute.
