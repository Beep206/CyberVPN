# CyberVPN App Store Metadata Guide

This document provides a complete overview of the App Store and Google Play metadata structure for CyberVPN mobile app.

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Metadata Files](#metadata-files)
4. [Screenshots](#screenshots)
5. [Fastlane Integration](#fastlane-integration)
6. [Upload Process](#upload-process)
7. [Verification](#verification)

## Overview

All app store metadata and assets for CyberVPN are organized in this directory structure. The metadata is available in English (en-US/en-EN) and Russian (ru-RU) to support our primary markets.

### Platforms Supported
- **iOS**: App Store Connect
- **Android**: Google Play Console

### Languages Supported
- English (en-US/en-EN)
- Russian (ru-RU)

## Directory Structure

```
cybervpn_mobile/
├── docs/app-store/
│   ├── store-metadata-en.json          # English metadata (source)
│   ├── store-metadata-ru.json          # Russian metadata (source)
│   ├── screenshots/
│   │   ├── ios/
│   │   │   ├── README.md               # iOS screenshot guide
│   │   │   ├── screenshot-config.json  # iOS screenshot specs
│   │   │   ├── ios-6.7-*.png          # iPhone 6.7" screenshots
│   │   │   ├── ios-6.5-*.png          # iPhone 6.5" screenshots
│   │   │   └── ipad-12.9-*.png        # iPad Pro screenshots
│   │   └── android/
│   │       ├── README.md               # Android screenshot guide
│   │       ├── screenshot-config.json  # Android screenshot specs
│   │       ├── feature-graphic-design-spec.md
│   │       ├── android-phone-*.png    # Phone screenshots
│   │       └── feature-graphic.png    # Required 1024x500 banner
│   └── APP_STORE_METADATA_GUIDE.md    # This file
│
└── fastlane/
    └── metadata/
        ├── en-US/                      # iOS English metadata
        │   ├── name.txt
        │   ├── subtitle.txt
        │   ├── description.txt
        │   ├── keywords.txt
        │   ├── promotional_text.txt
        │   ├── privacy_url.txt
        │   ├── support_url.txt
        │   └── release_notes.txt
        ├── ru-RU/                      # iOS Russian metadata
        │   └── [same files as en-US]
        └── android/
            ├── en-US/                  # Android English metadata
            │   ├── title.txt
            │   ├── short_description.txt
            │   └── full_description.txt
            └── ru-RU/                  # Android Russian metadata
                └── [same files as en-US]
```

## Metadata Files

### Source Files (JSON)

The canonical source for all metadata is in JSON format:

- **`store-metadata-en.json`**: English metadata for both iOS and Android
- **`store-metadata-ru.json`**: Russian metadata for both iOS and Android

These files contain:
- App names (30 char limit)
- Subtitles/short descriptions (30 char iOS, 80 char Android)
- Full descriptions (4000 char limit)
- Keywords (100 char limit for iOS)
- Privacy policy URLs
- Support information
- Copyright text
- Release notes

### iOS App Store Metadata

Located in `fastlane/metadata/{locale}/`:

| File | Character Limit | Description |
|------|-----------------|-------------|
| `name.txt` | 30 | App name displayed on App Store |
| `subtitle.txt` | 30 | Short tagline below app name |
| `description.txt` | 4000 | Full app description |
| `keywords.txt` | 100 | Comma-separated keywords |
| `promotional_text.txt` | 170 | Promotional text (updatable without review) |
| `privacy_url.txt` | - | Privacy policy URL |
| `support_url.txt` | - | Support website URL |
| `release_notes.txt` | 4000 | What's new in this version |

**Current Values (English)**:
- App Name: "CyberVPN - Secure Privacy" (25 chars ✓)
- Subtitle: "Fast & Anonymous VPN" (20 chars ✓)
- Keywords: 88 chars ✓
- Primary Category: Utilities
- Secondary Category: Productivity

### Google Play Metadata

Located in `fastlane/metadata/android/{locale}/`:

| File | Character Limit | Description |
|------|-----------------|-------------|
| `title.txt` | 30 | App title |
| `short_description.txt` | 80 | Brief description for search |
| `full_description.txt` | 4000 | Full app description |

**Current Values (English)**:
- Title: "CyberVPN - Secure Privacy" (25 chars ✓)
- Short Description: 75 chars ✓
- Category: Tools
- Content Rating: Everyone

## Screenshots

### iOS App Store

Required screenshot sizes:

1. **iPhone 6.7" Display** (1290 x 2796 pixels)
   - Devices: iPhone 14/15/16 Pro Max
   - Files: `ios-6.7-1.png` through `ios-6.7-5.png`

2. **iPhone 6.5" Display** (1242 x 2688 pixels)
   - Devices: iPhone 11 Pro Max, XS Max
   - Files: `ios-6.5-1.png` through `ios-6.5-5.png`

3. **iPad Pro 12.9"** (2048 x 2732 pixels)
   - Devices: iPad Pro 12.9" (2nd gen+)
   - Files: `ipad-12.9-1.png` through `ipad-12.9-5.png`

**Screenshot Content Order**:
1. Main dashboard with 3D globe
2. Server selection screen
3. Active connection with stats
4. Settings/profile screen
5. Subscription plans

See `docs/app-store/screenshots/ios/README.md` for detailed generation instructions.

### Google Play Store

**Phone Screenshots**:
- Recommended: 1080 x 1920 pixels (portrait)
- Minimum: 320 x 320 pixels
- Maximum: 3840 x 3840 pixels
- Quantity: 2-8 screenshots (8 recommended)
- Files: `android-phone-1.png` through `android-phone-8.png`

**Feature Graphic** (REQUIRED):
- Exact size: 1024 x 500 pixels
- Format: PNG or JPEG (24-bit RGB, no alpha)
- File: `feature-graphic.png`

**Screenshot Content Order**:
1. Main dashboard
2. Server selection
3. Active connection
4. Settings
5. Subscription plans
6. Profile/account
7. Security features
8. Statistics/analytics

See `docs/app-store/screenshots/android/README.md` and `feature-graphic-design-spec.md` for detailed instructions.

## Fastlane Integration

### iOS Deployment

Use fastlane to upload metadata and screenshots to App Store Connect:

```bash
cd cybervpn_mobile
fastlane ios upload_metadata
```

This reads from `fastlane/metadata/` and uploads to App Store Connect.

### Android Deployment

Use fastlane to upload to Google Play Console:

```bash
cd cybervpn_mobile
fastlane android upload_metadata
```

This reads from `fastlane/metadata/android/` and uploads to Play Console.

### Manual Configuration

If fastlane is not configured for metadata upload, you can manually upload via:

- **iOS**: App Store Connect web interface
- **Android**: Google Play Console web interface

## Upload Process

### iOS App Store Connect

1. Log in to [App Store Connect](https://appstoreconnect.apple.com)
2. Select your app
3. Navigate to "App Store" tab
4. Select version to edit
5. Upload metadata:
   - App name, subtitle, description
   - Keywords
   - Promotional text
   - Privacy policy URL
   - Support URL
6. Upload screenshots for each device size
7. Add release notes
8. Save changes

### Google Play Console

1. Log in to [Google Play Console](https://play.google.com/console)
2. Select your app
3. Navigate to "Store presence" → "Main store listing"
4. Upload metadata:
   - App name
   - Short description
   - Full description
5. Upload screenshots:
   - Phone screenshots (8 images)
   - Feature graphic (1024 x 500)
6. Add category and content rating
7. Save changes

## Verification

### Pre-Upload Checklist

#### iOS
- [ ] App name ≤ 30 characters
- [ ] Subtitle ≤ 30 characters
- [ ] Description ≤ 4000 characters
- [ ] Keywords ≤ 100 characters
- [ ] Privacy policy URL is accessible
- [ ] Support URL is accessible
- [ ] Screenshots match required dimensions exactly
- [ ] Minimum 3 screenshots per device size
- [ ] Screenshots show actual app UI
- [ ] No debug overlays visible

#### Android
- [ ] App title ≤ 30 characters
- [ ] Short description ≤ 80 characters
- [ ] Full description ≤ 4000 characters
- [ ] Feature graphic is exactly 1024 x 500 pixels
- [ ] Feature graphic has no transparency
- [ ] Phone screenshots ≥ 320 x 320 pixels
- [ ] Minimum 2 screenshots uploaded
- [ ] Screenshots show actual app UI

### Character Count Verification

Run the verification script:

```bash
cd docs/app-store
./verify-limits.sh
```

This checks all character limits against App Store and Play Store requirements.

### Screenshot Dimension Verification

```bash
# Check iOS screenshots
for file in docs/app-store/screenshots/ios/*.png; do
  identify -format "%f: %wx%h\n" "$file"
done

# Check Android screenshots
for file in docs/app-store/screenshots/android/*.png; do
  identify -format "%f: %wx%h\n" "$file"
done
```

## Design Guidelines

### Cyberpunk Theme

All screenshots and the feature graphic should showcase the app's cyberpunk aesthetic:

**Colors**:
- Matrix Green: #00FF88
- Neon Cyan: #00FFFF
- Neon Pink: #FF00FF
- Deep Navy: #0A0E1A
- Dark Background: #111827

**Typography**:
- Display: Orbitron (Google Fonts)
- Data/Stats: JetBrains Mono
- Body: System default

**Effects**:
- Neon glows on cards and buttons
- Scanline overlay
- 3D card transforms
- Matrix-inspired animations

### Screenshot Best Practices

1. **Status Bar**: Show clean time (9:41 AM) or hide status bar
2. **Theme**: Use dark cyberpunk theme for visual consistency
3. **Data**: Use realistic mock data, not real user information
4. **Quality**: Capture at exact required dimensions, PNG format
5. **Content**: Show key app features in each screenshot
6. **Order**: Most important screens first (dashboard, servers, connection)

## Localization

### Adding New Languages

To add a new language (e.g., Spanish):

1. Create JSON metadata file: `store-metadata-es.json`
2. Translate all text content
3. Create fastlane directories:
   ```bash
   mkdir -p fastlane/metadata/es-ES
   mkdir -p fastlane/metadata/android/es-ES
   ```
4. Generate fastlane metadata files from JSON
5. Capture localized screenshots (if UI text is localized)
6. Upload via fastlane or manually

### Current Translations

- ✅ English (en-US/en-EN)
- ✅ Russian (ru-RU)

## Privacy Policy

The privacy policy URL referenced in metadata must be publicly accessible:

**URL**: https://cybervpn.com/privacy

Ensure this URL:
- Returns HTTP 200 status
- Contains valid privacy policy text
- Is accessible without authentication
- Complies with GDPR, CCPA, and other regulations
- Matches the privacy practices in your app

## Support Information

**Support URL**: https://cybervpn.com/support
**Support Email**: support@cybervpn.com

Ensure these are monitored and responsive.

## Age Ratings

- **iOS**: 4+ (No objectionable content)
- **Android**: Everyone (Suitable for all ages)

VPN apps are typically rated for all ages unless they contain additional features like social networking or user-generated content.

## App Categories

### iOS
- **Primary**: Utilities
- **Secondary**: Productivity

### Android
- **Category**: Tools

These categories optimize discoverability for VPN applications.

## Copyright

© 2025 CyberVPN. All rights reserved.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-02-01 | Initial release metadata |

## Maintenance

### Updating Metadata

1. Edit source JSON files (`store-metadata-en.json`, `store-metadata-ru.json`)
2. Regenerate fastlane metadata files:
   ```bash
   ./scripts/generate-fastlane-metadata.sh
   ```
3. Verify character limits: `./verify-limits.sh`
4. Upload via fastlane or manually

### Updating Screenshots

1. Build latest app version
2. Navigate to each screen
3. Capture screenshots at required dimensions
4. Verify dimensions: `identify screenshot.png`
5. Replace existing files in `screenshots/` directories
6. Upload via fastlane or manually

## Troubleshooting

### Common Issues

**"App name too long"**
- iOS limit: 30 characters
- Android limit: 30 characters
- Solution: Shorten name or remove subtitle elements

**"Keywords exceed limit"**
- iOS limit: 100 characters (including commas)
- Solution: Remove less important keywords
- Tip: Focus on high-volume search terms

**"Screenshot wrong dimensions"**
- iOS: Exact dimensions required
- Android: Minimum 320x320
- Solution: Recapture at correct size or resize with quality tools

**"Feature graphic rejected"**
- Common reason: Contains transparency
- Solution: Flatten image, ensure RGB-24 format
- Verify: `identify -verbose feature-graphic.png` shows no alpha

**"Privacy policy URL not accessible"**
- App Store Connect and Play Console both verify the URL
- Solution: Ensure URL returns HTTP 200, no authentication required

## Resources

- [App Store Connect Help](https://developer.apple.com/app-store-connect/)
- [Google Play Console Help](https://support.google.com/googleplay/android-developer/)
- [iOS App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Google Play Developer Policy](https://play.google.com/about/developer-content-policy/)
- [Fastlane Documentation](https://docs.fastlane.tools/)

## Contact

For questions about app store metadata:
- Technical: tech@cybervpn.com
- Marketing: marketing@cybervpn.com
- Support: support@cybervpn.com
