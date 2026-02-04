# CyberVPN iOS Widget

This directory contains the iOS WidgetKit extension for CyberVPN.

## Setup Required in Xcode

This widget extension requires manual configuration in Xcode that cannot be automated via command line. The Swift files are ready, but the following steps must be completed:

### 1. Create Widget Extension Target
1. Open `ios/Runner.xcworkspace` in Xcode
2. File → New → Target
3. Select "Widget Extension"
4. Product Name: `CyberVPNWidget`
5. Bundle Identifier: `com.cybervpn.cybervpnmobile.CyberVPNWidget`
6. Language: Swift
7. Uncheck "Include Configuration Intent"
8. Create target

### 2. Add Swift Files to Target
1. In Xcode Project Navigator, select the files in `ios/CyberVPNWidget/`
2. In File Inspector (right panel), under "Target Membership", check `CyberVPNWidget`
3. Ensure all `.swift` files are included:
   - CyberVPNWidget.swift
   - VPNStatusProvider.swift
   - CyberVPNWidgetEntry.swift
   - SmallWidgetView.swift
   - MediumWidgetView.swift

### 3. Configure App Group (Runner Target)
1. Select Runner target
2. Signing & Capabilities tab
3. Click "+ Capability"
4. Add "App Groups"
5. Click "+" to add new App Group: `group.com.cybervpn.widgets`
6. Ensure checkbox is checked

### 4. Configure App Group (Widget Target)
1. Select CyberVPNWidget target
2. Signing & Capabilities tab
3. Click "+ Capability"
4. Add "App Groups"
5. Select existing group: `group.com.cybervpn.widgets`
6. Ensure checkbox is checked

### 5. Update Runner's Info.plist
Add URL scheme for deep linking (if not already present):
```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleTypeRole</key>
        <string>Editor</string>
        <key>CFBundleURLName</key>
        <string>com.cybervpn.cybervpnmobile</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>cybervpn</string>
        </array>
    </dict>
</array>
```

### 6. Build Configuration
Ensure deployment target for CyberVPNWidget is iOS 14.0 or higher:
1. Select CyberVPNWidget target
2. Build Settings tab
3. Search for "iOS Deployment Target"
4. Set to iOS 14.0

## Widget Sizes

### Small Widget (systemSmall)
- Status icon (checkmark.shield / xmark.shield / arrow.clockwise)
- Status text (CONNECTED / DISCONNECTED / CONNECTING)
- Cyberpunk themed colors

### Medium Widget (systemMedium)
- Status icon and text (left side)
- Server name with server.rack icon
- Upload speed with up arrow icon (matrix green)
- Download speed with down arrow icon (neon cyan)

## Data Sharing

The widget reads VPN status from shared UserDefaults using App Group `group.com.cybervpn.widgets`.

Data keys:
- `vpn_status`: "connected" | "disconnected" | "connecting"
- `server_name`: Current server name or "Not connected"
- `upload_speed`: Formatted upload speed (e.g., "1.2 MB/s")
- `download_speed`: Formatted download speed (e.g., "5.8 MB/s")
- `last_update`: ISO 8601 timestamp of last update

## Deep Linking

Tapping the widget opens the app via `cybervpn://widget-action` URL scheme and navigates to the VPN control screen.

## Timeline Updates

The widget uses a 15-minute refresh policy. The TimelineProvider requests a new timeline after 15 minutes, but the app can trigger immediate updates via `HomeWidget.updateWidget()` when VPN state changes.

## Cyberpunk Theme Colors

- Matrix Green: `#00ff88` - Connected state, upload speed
- Neon Cyan: `#00ffff` - Connecting state, download speed, server icon
- Neon Pink: `#ff00ff` - Disconnected state
- Dark Background: Gradient from `#0A0E1A` to `#1A1F35`

## Testing

1. Build and run the app on a physical device or simulator (iOS 14+)
2. Long-press home screen
3. Tap "+" to add widget
4. Search for "CyberVPN"
5. Add small and/or medium widgets
6. Connect VPN in the app and verify widget updates
7. Tap widget to verify deep link navigation

## Troubleshooting

### Widget not showing in gallery
- Verify widget target builds successfully
- Check that App Group is configured correctly
- Ensure iOS deployment target is 14.0+

### Widget shows "Unable to Load"
- Check App Group ID matches in both targets: `group.com.cybervpn.widgets`
- Verify App Group capability is enabled in Apple Developer account
- Check Console.app for widget extension errors

### Widget not updating
- Verify `HomeWidget.setAppGroupId()` is called in Flutter app
- Check that data is being written to shared UserDefaults
- Use Console.app to view widget extension logs

### Deep link not working
- Verify URL scheme `cybervpn` is registered in Runner's Info.plist
- Check that deep link handler is initialized in Flutter app
- Test with app in different states (closed, backgrounded, foreground)

## Files

- `CyberVPNWidget.swift` - Widget bundle and widget definitions
- `VPNStatusProvider.swift` - Timeline provider for widget updates
- `CyberVPNWidgetEntry.swift` - Entry model and VPN status enum
- `SmallWidgetView.swift` - Small widget UI (systemSmall)
- `MediumWidgetView.swift` - Medium widget UI (systemMedium)
- `Info.plist` - Widget extension configuration

## References

- [WidgetKit Documentation](https://developer.apple.com/documentation/widgetkit)
- [home_widget Package](https://pub.dev/packages/home_widget)
- [App Groups Guide](https://developer.apple.com/documentation/bundleresources/entitlements/com_apple_security_application-groups)
