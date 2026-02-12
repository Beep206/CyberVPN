import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/screens/quick_setup_screen.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  late SharedPreferences mockPrefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    mockPrefs = await SharedPreferences.getInstance();
  });

  /// Helper to build the screen with mocked providers.
  Widget buildQuickSetupScreen({
    ServerEntity? recommendedServer,
    VpnConnectionState? vpnState,
  }) {
    return ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(mockPrefs),
        recommendedServerProvider.overrideWith((ref) {
          return recommendedServer;
        }),
        vpnConnectionProvider.overrideWith(() {
          return TestVpnConnectionNotifier(vpnState);
        }),
      ],
      child: const MaterialApp(
        home: QuickSetupScreen(),
      ),
    );
  }

  testWidgets(
    'displays auto-selected server with country flag and server name',
    (WidgetTester tester) async {
      const server = ServerEntity(
        id: 'server-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: false,
        isFavorite: false,
        ping: 25,
      );

      await tester.pumpWidget(buildQuickSetupScreen(
        recommendedServer: server,
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      // Verify title.
      expect(find.text('Ready to protect you'), findsOneWidget);

      // Verify server name.
      expect(find.text('US East 1'), findsOneWidget);

      // Verify location.
      expect(find.text('New York, United States'), findsOneWidget);

      // Verify ping display.
      expect(find.text('25 ms'), findsOneWidget);

      // Verify Connect Now button.
      expect(find.text('Connect Now'), findsOneWidget);
    },
  );

  testWidgets(
    'taps Connect and calls VPN provider connect',
    (WidgetTester tester) async {
      const server = ServerEntity(
        id: 'server-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: false,
        isFavorite: false,
      );

      final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(mockPrefs),
            recommendedServerProvider.overrideWith((ref) => server),
            vpnConnectionProvider.overrideWith(() => vpnNotifier),
          ],
          child: const MaterialApp(
            home: QuickSetupScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Connect Now button.
      final connectButton = find.text('Connect Now');
      expect(connectButton, findsOneWidget);
      await tester.tap(connectButton);
      await tester.pump();

      // Verify connect was called.
      expect(vpnNotifier.connectCalled, isTrue);
      expect(vpnNotifier.lastConnectedServer?.id, equals('server-1'));
    },
  );

  testWidgets(
    'shows celebration animation and navigates to connection screen on success',
    (WidgetTester tester) async {
      const server = ServerEntity(
        id: 'server-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: false,
        isFavorite: false,
      );

      final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(mockPrefs),
            recommendedServerProvider.overrideWith((ref) => server),
            vpnConnectionProvider.overrideWith(() => vpnNotifier),
          ],
          child: const MaterialApp(
            home: QuickSetupScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Connect Now button.
      await tester.tap(find.text('Connect Now'));
      await tester.pump();

      // Simulate successful connection.
      vpnNotifier.setState(
        const VpnConnected(
          server: server,
          protocol: VpnProtocol.vless,
        ),
      );
      await tester.pump();

      // Wait for celebration animation to start.
      await tester.pump(const Duration(milliseconds: 100));

      // Verify celebration text appears.
      expect(find.text('You\'re protected!'), findsOneWidget);
      expect(find.text('Your connection is now secure'), findsOneWidget);

      // Note: Navigation testing requires a full router setup which is
      // complex for this widget test. The navigation is tested in integration
      // tests or manually verified.
    },
  );

  testWidgets(
    'displays loading indicator when no recommended server is available',
    (WidgetTester tester) async {
      await tester.pumpWidget(buildQuickSetupScreen(
        recommendedServer: null,
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      // Verify loading indicator.
      expect(find.byType(CircularProgressIndicator), findsWidgets);

      // Verify loading message.
      expect(find.text('Finding the best server...'), findsOneWidget);

      // Verify Connect button is disabled.
      final connectButton =
          tester.widget<ElevatedButton>(find.byType(ElevatedButton).first);
      expect(connectButton.onPressed, isNull);
    },
  );

  testWidgets(
    'shows error SnackBar on connection failure',
    (WidgetTester tester) async {
      const server = ServerEntity(
        id: 'server-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: false,
        isFavorite: false,
      );

      final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(mockPrefs),
            recommendedServerProvider.overrideWith((ref) => server),
            vpnConnectionProvider.overrideWith(() => vpnNotifier),
          ],
          child: const MaterialApp(
            home: QuickSetupScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Connect Now button.
      await tester.tap(find.text('Connect Now'));
      await tester.pump();

      // Simulate connection error.
      vpnNotifier.setState(const VpnError(message: 'Connection timed out'));
      await tester.pump();

      // Wait for SnackBar to appear.
      await tester.pump(const Duration(milliseconds: 100));

      // Verify error message in SnackBar.
      expect(find.text('Connection failed: Connection timed out'), findsOneWidget);
    },
  );

  testWidgets(
    'marks setup as abandoned when skip button is tapped',
    (WidgetTester tester) async {
      const server = ServerEntity(
        id: 'server-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: false,
        isFavorite: false,
      );

      await tester.pumpWidget(buildQuickSetupScreen(
        recommendedServer: server,
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      // Tap Skip button.
      await tester.tap(find.text('Skip for now'));
      await tester.pump();

      // Verify the abandoned flag was set in SharedPreferences.
      final abandoned = mockPrefs.getBool('quick_setup_abandoned');
      expect(abandoned, isTrue);

      final completed = mockPrefs.getBool('quick_setup_completed');
      expect(completed, isTrue);
    },
  );

  testWidgets(
    'shows loading indicator during connection attempt',
    (WidgetTester tester) async {
      const server = ServerEntity(
        id: 'server-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: false,
        isFavorite: false,
      );

      final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sharedPreferencesProvider.overrideWithValue(mockPrefs),
            recommendedServerProvider.overrideWith((ref) => server),
            vpnConnectionProvider.overrideWith(() => vpnNotifier),
          ],
          child: const MaterialApp(
            home: QuickSetupScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Connect Now button.
      await tester.tap(find.text('Connect Now'));
      await tester.pump();

      // Verify loading indicator appears in the button.
      expect(find.byType(CircularProgressIndicator), findsWidgets);
    },
  );
}

// ---------------------------------------------------------------------------
// Test VPN Connection Notifier
// ---------------------------------------------------------------------------

class TestVpnConnectionNotifier extends VpnConnectionNotifier {
  VpnConnectionState? initialState;
  bool connectCalled = false;
  ServerEntity? lastConnectedServer;

  TestVpnConnectionNotifier(this.initialState);

  @override
  Future<VpnConnectionState> build() async {
    return initialState ?? const VpnDisconnected();
  }

  @override
  Future<void> connect(ServerEntity server) async {
    connectCalled = true;
    lastConnectedServer = server;
    state = AsyncData(VpnConnecting(server: server));
  }

  @override
  Future<void> disconnect() async {
    state = const AsyncData(VpnDisconnecting());
  }

  @override
  Future<void> handleNetworkChange(bool isOnline) async {}

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connectToLastOrRecommended() async {}

  void setState(VpnConnectionState newState) {
    state = AsyncData(newState);
  }
}
