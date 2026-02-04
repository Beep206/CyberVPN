# Task 95: iOS WidgetKit Implementation Guide

## Status: BLOCKED - Requires Xcode Environment

This task requires:
1. macOS system with Xcode 14.0+
2. iOS Simulator or physical iOS device for testing
3. Apple Developer account for App Group capabilities
4. Direct access to Xcode project for target creation and configuration

## Implementation Overview

### Architecture
- **Widget Extension**: Swift WidgetKit target in `ios/CyberVPNWidget/`
- **Data Sharing**: App Group + UserDefaults for Flutter → Widget communication
- **UI**: SwiftUI with cyberpunk theme (matrix green #00ff88, neon cyan #00ffff)
- **Updates**: Timeline Provider with 15-minute refresh intervals
- **Deep Linking**: Custom URL scheme for widget tap → app navigation

## Subtask 1: Create WidgetKit Extension and Configure App Group

### Steps Required in Xcode

#### 1.1 Create Widget Extension Target
1. Open `ios/Runner.xcworkspace` in Xcode
2. File → New → Target
3. Select "Widget Extension"
4. Product Name: `CyberVPNWidget`
5. Bundle Identifier: `com.cybervpn.cybervpnmobile.CyberVPNWidget`
6. Language: Swift
7. Uncheck "Include Configuration Intent"
8. Create target

#### 1.2 Configure App Group for Runner (Main App)
1. Select Runner target
2. Signing & Capabilities tab
3. Click "+ Capability"
4. Add "App Groups"
5. Click "+" to add new App Group: `group.com.cybervpn.widgets`
6. Ensure checkbox is checked

#### 1.3 Configure App Group for Widget Extension
1. Select CyberVPNWidget target
2. Signing & Capabilities tab
3. Click "+ Capability"
4. Add "App Groups"
5. Select existing group: `group.com.cybervpn.widgets`
6. Ensure checkbox is checked

#### 1.4 Update Runner's Info.plist
Add URL scheme for deep linking:
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

#### 1.5 Update Flutter Dependencies
Already present in `pubspec.yaml`:
```yaml
dependencies:
  home_widget: ^0.8.0
```

### 1.6 Flutter Side: Data Sharing Implementation

Create `lib/features/vpn/data/datasources/widget_data_source.dart`:

```dart
import 'package:home_widget/home_widget.dart';

class WidgetDataSource {
  static const String _appGroupId = 'group.com.cybervpn.widgets';

  /// Update widget with current VPN status
  Future<void> updateWidgetData({
    required String status, // 'connected', 'disconnected', 'connecting'
    required String serverName,
    required String uploadSpeed,
    required String downloadSpeed,
  }) async {
    try {
      await HomeWidget.saveWidgetData('vpn_status', status);
      await HomeWidget.saveWidgetData('server_name', serverName);
      await HomeWidget.saveWidgetData('upload_speed', uploadSpeed);
      await HomeWidget.saveWidgetData('download_speed', downloadSpeed);
      await HomeWidget.saveWidgetData('last_update', DateTime.now().toIso8601String());

      // Trigger widget update
      await HomeWidget.updateWidget(
        iOSName: 'CyberVPNWidget',
      );
    } catch (e) {
      // Log error but don't crash
      print('Error updating widget data: $e');
    }
  }

  /// Initialize widget on app startup
  Future<void> initialize() async {
    await HomeWidget.setAppGroupId(_appGroupId);
  }
}
```

### 1.7 Integrate with VPN State Management

Update VPN connection state provider to update widget:

```dart
// In lib/features/vpn/presentation/providers/vpn_connection_provider.dart
// Add widget data source injection and update calls

class VpnConnectionNotifier extends StateNotifier<VpnConnectionState> {
  final WidgetDataSource _widgetDataSource;

  VpnConnectionNotifier(this._widgetDataSource) : super(const VpnConnectionState.disconnected());

  Future<void> connect(Server server) async {
    state = const VpnConnectionState.connecting();
    await _widgetDataSource.updateWidgetData(
      status: 'connecting',
      serverName: server.name,
      uploadSpeed: '0 KB/s',
      downloadSpeed: '0 KB/s',
    );

    // ... connection logic ...

    state = VpnConnectionState.connected(server: server);
    await _widgetDataSource.updateWidgetData(
      status: 'connected',
      serverName: server.name,
      uploadSpeed: _currentUploadSpeed,
      downloadSpeed: _currentDownloadSpeed,
    );
  }

  Future<void> disconnect() async {
    // ... disconnection logic ...

    await _widgetDataSource.updateWidgetData(
      status: 'disconnected',
      serverName: 'Not connected',
      uploadSpeed: '0 KB/s',
      downloadSpeed: '0 KB/s',
    );
  }
}
```

### 1.8 Initialize Widget in main.dart

```dart
// In lib/main.dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize widget data source
  final widgetDataSource = WidgetDataSource();
  await widgetDataSource.initialize();

  // ... rest of initialization ...
}
```

### Verification
- Build Flutter app: `flutter build ios`
- Open Xcode workspace: `open ios/Runner.xcworkspace`
- Check Signing & Capabilities for both targets show App Group
- Run app on simulator/device
- Check Console.app for any App Group permission errors

---

## Subtask 2: Implement Widget Views and Timeline Provider

### 2.1 Create Widget Entry Model

Create `ios/CyberVPNWidget/CyberVPNWidgetEntry.swift`:

```swift
import WidgetKit
import SwiftUI

struct VPNStatusEntry: TimelineEntry {
    let date: Date
    let status: VPNStatus
    let serverName: String
    let uploadSpeed: String
    let downloadSpeed: String

    enum VPNStatus: String {
        case connected
        case disconnected
        case connecting

        var displayText: String {
            switch self {
            case .connected: return "CONNECTED"
            case .disconnected: return "DISCONNECTED"
            case .connecting: return "CONNECTING"
            }
        }

        var iconName: String {
            switch self {
            case .connected: return "checkmark.shield.fill"
            case .disconnected: return "xmark.shield.fill"
            case .connecting: return "arrow.clockwise.circle.fill"
            }
        }

        var color: Color {
            switch self {
            case .connected: return Color(hex: "00ff88") // Matrix green
            case .disconnected: return Color(hex: "ff00ff") // Neon pink
            case .connecting: return Color(hex: "00ffff") // Neon cyan
            }
        }
    }
}

// Color extension for hex colors
extension Color {
    init(hex: String) {
        let scanner = Scanner(string: hex)
        var rgbValue: UInt64 = 0
        scanner.scanHexInt64(&rgbValue)

        let r = Double((rgbValue & 0xFF0000) >> 16) / 255.0
        let g = Double((rgbValue & 0x00FF00) >> 8) / 255.0
        let b = Double(rgbValue & 0x0000FF) / 255.0

        self.init(red: r, green: g, blue: b)
    }
}
```

### 2.2 Create Timeline Provider

Create `ios/CyberVPNWidget/VPNStatusProvider.swift`:

```swift
import WidgetKit
import SwiftUI

struct VPNStatusProvider: TimelineProvider {
    private let appGroupId = "group.com.cybervpn.widgets"

    // Placeholder shown in widget gallery
    func placeholder(in context: Context) -> VPNStatusEntry {
        VPNStatusEntry(
            date: Date(),
            status: .disconnected,
            serverName: "Select Server",
            uploadSpeed: "0 KB/s",
            downloadSpeed: "0 KB/s"
        )
    }

    // Snapshot for transient display
    func getSnapshot(in context: Context, completion: @escaping (VPNStatusEntry) -> Void) {
        let entry = loadCurrentStatus()
        completion(entry)
    }

    // Timeline for widget updates
    func getTimeline(in context: Context, completion: @escaping (Timeline<VPNStatusEntry>) -> Void) {
        let currentEntry = loadCurrentStatus()

        // Create timeline with single entry, refresh after 15 minutes
        let refreshDate = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!
        let timeline = Timeline(entries: [currentEntry], policy: .after(refreshDate))

        completion(timeline)
    }

    // Load current status from shared UserDefaults
    private func loadCurrentStatus() -> VPNStatusEntry {
        guard let userDefaults = UserDefaults(suiteName: appGroupId) else {
            return placeholder(in: Context())
        }

        let statusString = userDefaults.string(forKey: "vpn_status") ?? "disconnected"
        let status = VPNStatusEntry.VPNStatus(rawValue: statusString) ?? .disconnected
        let serverName = userDefaults.string(forKey: "server_name") ?? "Not connected"
        let uploadSpeed = userDefaults.string(forKey: "upload_speed") ?? "0 KB/s"
        let downloadSpeed = userDefaults.string(forKey: "download_speed") ?? "0 KB/s"

        return VPNStatusEntry(
            date: Date(),
            status: status,
            serverName: serverName,
            uploadSpeed: uploadSpeed,
            downloadSpeed: downloadSpeed
        )
    }
}
```

### 2.3 Create Small Widget View

Create `ios/CyberVPNWidget/SmallWidgetView.swift`:

```swift
import SwiftUI
import WidgetKit

struct SmallWidgetView: View {
    let entry: VPNStatusEntry

    var body: some View {
        ZStack {
            // Cyberpunk dark background
            LinearGradient(
                colors: [
                    Color(hex: "0A0E1A"),
                    Color(hex: "1A1F35")
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            VStack(spacing: 8) {
                // Status icon
                Image(systemName: entry.status.iconName)
                    .font(.system(size: 32, weight: .bold))
                    .foregroundColor(entry.status.color)

                // Status text
                Text(entry.status.displayText)
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundColor(entry.status.color)
                    .textCase(.uppercase)
            }
            .padding()
        }
        .widgetURL(URL(string: "cybervpn://widget-action"))
    }
}
```

### 2.4 Create Medium Widget View

Create `ios/CyberVPNWidget/MediumWidgetView.swift`:

```swift
import SwiftUI
import WidgetKit

struct MediumWidgetView: View {
    let entry: VPNStatusEntry

    var body: some View {
        ZStack {
            // Cyberpunk dark background
            LinearGradient(
                colors: [
                    Color(hex: "0A0E1A"),
                    Color(hex: "1A1F35")
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            HStack(spacing: 16) {
                // Left: Status icon
                VStack {
                    Image(systemName: entry.status.iconName)
                        .font(.system(size: 40, weight: .bold))
                        .foregroundColor(entry.status.color)

                    Text(entry.status.displayText)
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundColor(entry.status.color)
                        .textCase(.uppercase)
                }
                .frame(width: 80)

                // Right: Server info and speeds
                VStack(alignment: .leading, spacing: 8) {
                    // Server name
                    HStack {
                        Image(systemName: "server.rack")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "00ffff"))
                        Text(entry.serverName)
                            .font(.system(size: 13, weight: .semibold, design: .monospaced))
                            .foregroundColor(.white)
                            .lineLimit(1)
                    }

                    Divider()
                        .background(Color(hex: "00ff88").opacity(0.3))

                    // Upload speed
                    HStack {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "00ff88"))
                        Text(entry.uploadSpeed)
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundColor(Color(hex: "00ff88"))
                    }

                    // Download speed
                    HStack {
                        Image(systemName: "arrow.down.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "00ffff"))
                        Text(entry.downloadSpeed)
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundColor(Color(hex: "00ffff"))
                    }
                }
                .padding(.trailing, 8)

                Spacer()
            }
            .padding()
        }
        .widgetURL(URL(string: "cybervpn://widget-action"))
    }
}
```

### 2.5 Create Widget Bundle

Create/Replace `ios/CyberVPNWidget/CyberVPNWidget.swift`:

```swift
import WidgetKit
import SwiftUI

@main
struct CyberVPNWidgetBundle: WidgetBundle {
    var body: some Widget {
        SmallVPNWidget()
        MediumVPNWidget()
    }
}

struct SmallVPNWidget: Widget {
    let kind: String = "SmallVPNWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: VPNStatusProvider()) { entry in
            SmallWidgetView(entry: entry)
        }
        .configurationDisplayName("VPN Status")
        .description("Shows your current VPN connection status")
        .supportedFamilies([.systemSmall])
    }
}

struct MediumVPNWidget: Widget {
    let kind: String = "MediumVPNWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: VPNStatusProvider()) { entry in
            MediumWidgetView(entry: entry)
        }
        .configurationDisplayName("VPN Details")
        .description("Shows VPN status, server, and connection speeds")
        .supportedFamilies([.systemMedium])
    }
}

// Preview for Xcode canvas
struct CyberVPNWidget_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            SmallWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "US East",
                uploadSpeed: "1.2 MB/s",
                downloadSpeed: "5.8 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))

            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "US East",
                uploadSpeed: "1.2 MB/s",
                downloadSpeed: "5.8 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
        }
    }
}
```

### Verification
- Build widget extension in Xcode
- Run on simulator/device
- Long-press home screen → Add Widget → CyberVPN
- Add both small and medium widgets
- Verify placeholder shows correctly
- Connect VPN in Flutter app
- Check widget updates with connection status

---

## Subtask 3: Implement Deep Linking

### 3.1 Flutter Deep Link Handler

Create `lib/core/routing/deep_link_handler.dart`:

```dart
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:uni_links/uni_links.dart';
import 'dart:async';

part 'deep_link_handler.g.dart';

@riverpod
class DeepLinkHandler extends _$DeepLinkHandler {
  StreamSubscription? _subscription;

  @override
  void build() {
    _initializeDeepLinking();
  }

  void _initializeDeepLinking() {
    // Listen for deep links when app is already running
    _subscription = uriLinkStream.listen((Uri? uri) {
      if (uri != null) {
        _handleDeepLink(uri);
      }
    }, onError: (err) {
      print('Deep link error: $err');
    });

    // Check for initial deep link (app launched from widget tap)
    _getInitialLink();
  }

  Future<void> _getInitialLink() async {
    try {
      final uri = await getInitialUri();
      if (uri != null) {
        _handleDeepLink(uri);
      }
    } catch (e) {
      print('Failed to get initial link: $e');
    }
  }

  void _handleDeepLink(Uri uri) {
    // Handle cybervpn:// scheme
    if (uri.scheme == 'cybervpn') {
      switch (uri.host) {
        case 'widget-action':
          // Navigate to VPN control screen
          ref.read(goRouterProvider).go('/vpn');
          break;
        default:
          print('Unknown deep link: $uri');
      }
    }
  }

  void dispose() {
    _subscription?.cancel();
  }
}
```

### 3.2 Add uni_links Dependency

Update `pubspec.yaml`:
```yaml
dependencies:
  uni_links: ^0.5.1
```

Run: `flutter pub get`

### 3.3 Initialize Deep Link Handler in main.dart

```dart
// In lib/main.dart
import 'package:cybervpn_mobile/core/routing/deep_link_handler.dart';

class MyApp extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Initialize deep link handler
    ref.watch(deepLinkHandlerProvider);

    final router = ref.watch(goRouterProvider);

    return MaterialApp.router(
      routerConfig: router,
      // ... rest of config
    );
  }
}
```

### 3.4 iOS Native Deep Link Configuration

Update `ios/Runner/AppDelegate.swift`:

```swift
import UIKit
import Flutter

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  // Handle URL scheme deep links
  override func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey : Any] = [:]
  ) -> Bool {
    return super.application(app, open: url, options: options)
  }

  // Handle universal links (future enhancement)
  override func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
  ) -> Bool {
    return super.application(application, continue: userActivity, restorationHandler: restorationHandler)
  }
}
```

### Verification
1. Build and run app on iOS device/simulator
2. Add widget to home screen
3. Tap widget
4. Verify app launches (cold start) and navigates to VPN screen
5. Background app, tap widget again
6. Verify app comes to foreground (warm start) and shows VPN screen
7. Test with different VPN states (connected, disconnected, connecting)

---

## Testing Strategy

### Unit Tests
- Timeline Provider returns correct entries
- Timeline refresh interval is 15 minutes
- Data loading from UserDefaults works correctly
- Status color mapping is correct

### Integration Tests
1. **Widget Rendering**
   - Add small widget → displays correctly
   - Add medium widget → displays correctly
   - Widget shows placeholder when no data available

2. **Data Updates**
   - Connect VPN in app → widget updates within 1 second
   - Disconnect VPN → widget updates
   - Change servers → widget shows new server name
   - Speed changes → widget reflects current speeds

3. **Timeline Updates**
   - Widget auto-refreshes after 15 minutes
   - Manual app refresh triggers widget update
   - Background app state doesn't prevent updates

4. **Deep Linking**
   - Tap small widget (app closed) → app launches to VPN screen
   - Tap medium widget (app closed) → app launches to VPN screen
   - Tap widget (app backgrounded) → app foregrounds to VPN screen
   - Tap widget (app in foreground) → navigates to VPN screen

### Device Testing
Test on:
- iOS 16 (minimum supported)
- iOS 17
- iOS 18 (latest)
- iPhone SE (small screen)
- iPhone 14 Pro (standard screen)
- iPhone 14 Pro Max (large screen)

---

## File Structure After Implementation

```
ios/
├── CyberVPNWidget/
│   ├── CyberVPNWidget.swift              (Widget bundle)
│   ├── VPNStatusProvider.swift           (Timeline provider)
│   ├── CyberVPNWidgetEntry.swift         (Entry model)
│   ├── SmallWidgetView.swift             (Small widget UI)
│   ├── MediumWidgetView.swift            (Medium widget UI)
│   ├── Assets.xcassets/                  (Widget assets)
│   └── Info.plist                        (Widget configuration)
├── Runner/
│   ├── AppDelegate.swift                 (Updated for deep links)
│   ├── Info.plist                        (Updated with URL scheme)
│   └── Runner.entitlements               (App Group capability)
└── Runner.xcodeproj/
    └── project.pbxproj                   (Updated with widget target)
```

```
lib/
├── features/vpn/
│   └── data/datasources/
│       └── widget_data_source.dart       (Widget data sharing)
└── core/routing/
    └── deep_link_handler.dart            (Deep link handling)
```

---

## Dependencies

### Flutter (already in pubspec.yaml)
- `home_widget: ^0.8.0` ✓
- `go_router: ^17.0.0` ✓

### To Add
- `uni_links: ^0.5.1` (for deep linking)

### iOS Native
- WidgetKit framework (iOS 14+)
- SwiftUI framework
- App Groups capability

---

## Known Issues and Limitations

1. **Widget Update Frequency**: iOS limits widget updates. Timeline provider updates every 15 minutes, but immediate updates via `HomeWidget.updateWidget()` work when app is active.

2. **App Group Required**: Both main app and widget must share same App Group. This requires proper provisioning profile configuration in Apple Developer account.

3. **Memory Constraints**: Widgets have strict memory limits. Keep views simple and avoid heavy computations.

4. **Deep Link Cold Start**: First app launch after installation may not handle deep links until app has been opened manually once.

5. **Preview in Xcode**: Widget previews require proper simulator/device setup. Some SwiftUI previews may not render correctly in canvas.

---

## Future Enhancements

1. **Large Widget**: Add systemLarge family with more details (bandwidth graph, multiple servers)
2. **Widget Configuration**: Add IntentConfiguration for user-customizable widgets
3. **Interactive Widgets (iOS 17+)**: Add buttons for quick connect/disconnect
4. **Live Activities (iOS 16.1+)**: Show real-time connection status in Dynamic Island
5. **Timeline Optimization**: Use more intelligent refresh strategies based on VPN state
6. **Localization**: Support multiple languages in widget text

---

## References

- [WidgetKit Documentation](https://developer.apple.com/documentation/widgetkit)
- [home_widget Package](https://pub.dev/packages/home_widget)
- [App Groups Documentation](https://developer.apple.com/documentation/bundleresources/entitlements/com_apple_security_application-groups)
- [uni_links Package](https://pub.dev/packages/uni_links)
- [SwiftUI Widget Tutorial](https://developer.apple.com/tutorials/swiftui/creating-a-widget)
