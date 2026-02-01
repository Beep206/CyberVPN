# App Icon Assets

This directory contains the source assets for the CyberVPN mobile app icon.

## Source Files

### SVG Sources (Editable)
- **app_icon.svg** - Main app icon design (1024x1024)
  - Complete icon with background for iOS
  - Cyberpunk design: shield + lock + circuit patterns
  - Brand colors: matrix green, neon cyan, neon pink
  - Background gradient: deep navy (#0A0E1A) to dark (#111827)

- **app_icon_foreground.svg** - Adaptive icon foreground layer (1024x1024)
  - Shield and lock design only
  - Transparent background
  - Centered for Android adaptive icon safe zone (66% circle)

### PNG Exports (Generated)
- **app_icon.png** - 1024x1024 PNG for iOS and base image
- **app_icon_foreground.png** - 1024x1024 PNG for Android adaptive foreground

## Regenerating Icon Assets

If you need to modify the icon design:

1. **Edit SVG files** using any vector graphics editor (Figma, Inkscape, Adobe Illustrator)
   - Maintain 1024x1024 viewBox
   - Keep brand colors from `lib/app/theme/tokens.dart`
   - For foreground layer, keep design within center 66% circle

2. **Convert SVG to PNG**
   ```bash
   cd cybervpn_mobile
   node scripts/generate_icon.mjs
   ```

3. **Generate platform icons**
   ```bash
   flutter pub get
   dart run flutter_launcher_icons
   ```

## Design Specifications

### Colors
- Matrix Green: `#00FF88` (primary accent)
- Neon Cyan: `#00FFFF` (highlights)
- Neon Pink: `#FF00FF` (accents)
- Deep Navy: `#0A0E1A` (background)
- Dark BG: `#111827` (gradient)

### Design Elements
- **Shield**: Security/protection symbol
- **Lock**: VPN encryption/privacy
- **Circuit patterns**: Technology/networking theme
- **Glow effects**: Cyberpunk aesthetic
- **Gradient strokes**: Visual depth

### Platform Requirements

#### Android
- Adaptive icon with colored background (#0A0E1A)
- Foreground layer with transparency
- 16% inset for safe zone
- Supports circular, squircle, and square masks

#### iOS
- No transparency (solid background)
- All required sizes (20x20 to 1024x1024)
- 2x and 3x scale factors

## File Locations

After generation, platform-specific icons are created at:

- **Android**: `android/app/src/main/res/mipmap-*/ic_launcher.png`
- **Android Adaptive**: `android/app/src/main/res/mipmap-*/ic_launcher_foreground.png`
- **iOS**: `ios/Runner/Assets.xcassets/AppIcon.appiconset/`

See `docs/APP_ICON_VERIFICATION.md` for complete file listing and testing checklist.

## Tools Used

- **Design**: SVG (hand-coded, can be edited in any vector graphics tool)
- **Conversion**: sharp (Node.js image processing library)
- **Generation**: flutter_launcher_icons (Flutter package)

## References

- Flutter launcher icons: https://pub.dev/packages/flutter_launcher_icons
- Android adaptive icons: https://developer.android.com/develop/ui/views/launch/icon_design_adaptive
- iOS app icons: https://developer.apple.com/design/human-interface-guidelines/app-icons
