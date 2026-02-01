# iOS App Store Screenshots

This directory contains screenshots for iOS App Store submission.

## Required Sizes

### iPhone 6.7" Display (1290 x 2796 pixels)
- Devices: iPhone 14 Pro Max, iPhone 15 Pro Max, iPhone 16 Pro Max
- Files: `ios-6.7-1.png` through `ios-6.7-5.png`

### iPhone 6.5" Display (1242 x 2688 pixels)
- Devices: iPhone 11 Pro Max, iPhone XS Max
- Files: `ios-6.5-1.png` through `ios-6.5-5.png`

### iPad Pro 12.9" Display (2048 x 2732 pixels)
- Devices: iPad Pro 12.9" (2nd generation and later)
- Files: `ipad-12.9-1.png` through `ipad-12.9-5.png`

## Screenshot Content

Each screenshot set should include the following screens in order:

1. **Main Dashboard** (`*-1.png`)
   - 3D globe visualization
   - Server list with locations
   - Connection status
   - Cyberpunk theme with neon accents

2. **Server Selection** (`*-2.png`)
   - Full server list
   - Country flags
   - Ping/latency indicators
   - Server load indicators

3. **Connection Active** (`*-3.png`)
   - Connected state
   - Real-time statistics (upload/download speed)
   - Connection time counter
   - Traffic usage graphs

4. **Settings/Profile** (`*-4.png`)
   - User settings
   - Theme selector (showing cyberpunk theme)
   - Protocol selection
   - Security features (kill switch, split tunneling)

5. **Subscription Plans** (`*-5.png`)
   - Available subscription tiers
   - Feature comparison
   - Pricing information
   - Trial period highlight

## Generation Instructions

### Using iOS Simulator

1. Build the app in profile or debug mode:
   ```bash
   cd /home/beep/projects/VPNBussiness/cybervpn_mobile
   flutter build ios --debug
   ```

2. Open iOS Simulator with the required device:
   ```bash
   # iPhone 15 Pro Max (6.7")
   open -a Simulator --args -CurrentDeviceUDID [UDID]
   ```

3. Navigate to each screen and capture screenshots:
   - Use `Cmd + S` to save screenshot
   - Or use `xcrun simctl io booted screenshot screenshot.png`

4. Rename files according to the naming convention above.

### Screenshot Requirements

- **Format**: PNG (24-bit RGB)
- **Color Space**: sRGB or Display P3
- **Resolution**: Exact pixel dimensions required
- **Status Bar**: Can be hidden or shown with clean time (9:41 AM)
- **Theme**: Cyberpunk dark theme preferred
- **Data**: Use realistic mock data (server names, locations, speeds)
- **Text**: English for primary screenshots, Russian for localized version

### Design Considerations

- **Branding**: Matrix green (#00FF88), neon cyan (#00FFFF), neon pink (#FF00FF)
- **Background**: Deep navy (#0A0E1A) or dark background (#111827)
- **Typography**: Orbitron for headers, JetBrains Mono for data
- **Effects**: Neon glows, scanlines overlay, 3D card transforms
- **Clean UI**: No debug overlays, no development artifacts

## App Store Connect Upload

1. Log in to App Store Connect
2. Navigate to your app > App Store tab
3. Select the iOS version you're preparing
4. Scroll to "App Preview and Screenshots"
5. Upload screenshots for each required device size
6. Arrange screenshots in the desired order (drag and drop)
7. Save changes

## Notes

- Screenshots can have optional captions/overlays added in App Store Connect
- You can add localized screenshots for different languages
- First screenshot is the most important (appears in search results)
- Consider A/B testing different screenshot orders
- Update screenshots with each major app update

## Current Status

**TODO**: Generate actual screenshots from the Flutter app running on iOS simulators.

The app is fully functional and ready for screenshot capture. Key screens to capture:
- `lib/features/home/presentation/pages/home_page.dart` - Main dashboard
- `lib/features/servers/presentation/pages/server_list_page.dart` - Server selection
- `lib/features/connection/presentation/pages/connection_page.dart` - Active connection
- `lib/features/settings/presentation/pages/settings_page.dart` - Settings
- `lib/features/subscription/presentation/pages/subscription_plans_page.dart` - Plans
