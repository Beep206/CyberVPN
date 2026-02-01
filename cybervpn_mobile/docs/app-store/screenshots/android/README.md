# Google Play Store Screenshots

This directory contains screenshots and feature graphic for Google Play Store submission.

## Required Assets

### Phone Screenshots
- **Minimum size**: 320 x 320 pixels
- **Recommended size**: 1080 x 1920 pixels (portrait) or 1920 x 1080 pixels (landscape)
- **Maximum size**: 3840 x 3840 pixels
- **Format**: PNG or JPEG
- **Quantity**: Minimum 2, Maximum 8 screenshots
- **Files**: `android-phone-1.png` through `android-phone-8.png`

### Feature Graphic (REQUIRED)
- **Exact size**: 1024 x 500 pixels
- **Format**: PNG or JPEG (24-bit RGB, no alpha channel)
- **Usage**: Displayed at top of Play Store listing
- **File**: `feature-graphic.png`
- **Design**: Showcases app branding with cyberpunk theme

## Screenshot Content

Recommended 8 screenshots in the following order:

1. **Main Dashboard** (`android-phone-1.png`)
   - 3D globe visualization
   - Server list
   - Connection status
   - Quick connect button

2. **Server Selection** (`android-phone-2.png`)
   - Full server list with country flags
   - Ping indicators
   - Server load percentages
   - Search functionality

3. **Active Connection** (`android-phone-3.png`)
   - Connected state with statistics
   - Real-time upload/download speeds
   - Connection timer
   - Traffic graphs

4. **Settings** (`android-phone-4.png`)
   - Theme selector
   - Protocol selection
   - Security options
   - App preferences

5. **Subscription Plans** (`android-phone-5.png`)
   - Subscription tiers
   - Feature comparison
   - Pricing
   - Trial information

6. **Profile/Account** (`android-phone-6.png`)
   - User information
   - Subscription status
   - Traffic usage history
   - Account settings

7. **Security Features** (`android-phone-7.png`)
   - Kill switch toggle
   - Split tunneling configuration
   - DNS settings
   - Advanced security options

8. **Statistics/Analytics** (`android-phone-8.png`)
   - Connection history
   - Traffic usage charts
   - Server performance metrics
   - Usage statistics

## Feature Graphic Design

The feature graphic (1024 x 500 pixels) should include:

### Required Elements
- **App branding**: CyberVPN logo/icon
- **Tagline**: "Secure. Anonymous. Fast." or similar
- **Visual elements**: Globe, network lines, matrix effect
- **Color scheme**: Cyberpunk theme (matrix green, neon cyan, deep navy)

### Design Guidelines
- Text must be readable at thumbnail size (minimum 12pt font)
- No important content within 64 pixels of edges (safe zone)
- Avoid pure white or black backgrounds
- High contrast for text readability
- Consistent with app branding

### Sample Feature Graphic Layout
```
┌────────────────────────────────────────────────────┐
│  [APP ICON]    CYBERVPN                            │
│                                                    │
│  Secure. Anonymous. Fast.                         │
│                                  [3D GLOBE/NETWORK]│
│  Military-Grade VPN Protection                    │
└────────────────────────────────────────────────────┘
     1024 x 500 pixels
```

## Generation Instructions

### Using Android Emulator/Device

1. Build the app in profile or debug mode:
   ```bash
   cd /home/beep/projects/VPNBussiness/cybervpn_mobile
   flutter build apk --debug
   flutter install
   ```

2. Launch Android Emulator or connect device:
   ```bash
   # Start emulator (Pixel 6 or similar with 1080x1920)
   flutter emulators --launch [emulator_name]

   # Or use connected device
   adb devices
   ```

3. Capture screenshots:
   ```bash
   # Method 1: ADB screenshot command
   adb shell screencap -p /sdcard/screenshot.png
   adb pull /sdcard/screenshot.png

   # Method 2: Android Studio Device Manager
   # Click camera icon in Device Manager toolbar

   # Method 3: In-emulator
   # Power + Volume Down buttons
   ```

4. Rename and organize files according to naming convention.

### Creating Feature Graphic

Use design tools to create the 1024 x 500 pixel feature graphic:

**Design Tools**:
- Figma (recommended)
- Adobe Photoshop
- GIMP (free alternative)
- Canva

**Assets to include**:
- App icon from `assets/images/app_icon.png`
- Cyberpunk color palette (matrix green, neon cyan, deep navy)
- Typography: Orbitron font for title
- 3D globe or network visualization (can use screenshot from app)

## Screenshot Requirements

- **Format**: PNG or JPEG (PNG recommended)
- **Color Space**: sRGB
- **Resolution**: 1080 x 1920 (portrait) recommended
- **Status Bar**: Can be hidden or shown
- **Navigation Bar**: Can be hidden or shown
- **Theme**: Cyberpunk dark theme preferred
- **Data**: Use realistic mock data
- **Text**: English for primary screenshots

### Design Considerations

- **Branding Colors**:
  - Matrix green: #00FF88
  - Neon cyan: #00FFFF
  - Neon pink: #FF00FF
  - Deep navy: #0A0E1A
  - Dark background: #111827

- **Typography**:
  - Display: Orbitron
  - Data/Stats: JetBrains Mono
  - Body: System default

- **Effects**:
  - Neon glows on cards
  - Scanlines overlay
  - 3D card transforms

- **Clean UI**: No debug overlays, no development artifacts

## Google Play Console Upload

1. Log in to Google Play Console
2. Navigate to your app > Store presence > Main store listing
3. Scroll to "Phone screenshots" section
4. Upload screenshots (drag and drop or click to upload)
5. Upload feature graphic in the designated section
6. Arrange screenshots in desired order
7. Save changes

## Localization

You can provide localized screenshots for different languages:
- Navigate to "Manage translations" in Play Console
- Upload screenshots for each supported language (English, Russian, etc.)
- Feature graphic should be language-agnostic or localized

## Notes

- First 2 screenshots are most visible in store listings
- Feature graphic appears at top of store page on tablets and web
- Screenshots can have device frames added via Play Console
- Consider showing both portrait and landscape orientations
- Update screenshots with major app updates
- A/B test different screenshot orders for better conversion

## Current Status

**TODO**: Generate actual screenshots from the Flutter app running on Android emulator/device.

The app is fully functional and ready for screenshot capture. Same screens as iOS:
- Main dashboard with 3D globe
- Server selection list
- Active connection with statistics
- Settings and security features
- Subscription plans
- Profile/account screen
- Additional security options screen
- Statistics/analytics screen
