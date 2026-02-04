import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/screens/connection_screen.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connect_button.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connection_info.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';

import '../helpers/mock_factories.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testServer = createMockServer(
  id: 'us-east-1',
  name: 'US East 1',
  countryCode: 'US',
  countryName: 'United States',
  city: 'New York',
);

// ---------------------------------------------------------------------------
// Fake VPN connection notifier
// ---------------------------------------------------------------------------

/// A fake [VpnConnectionNotifier] that returns a pre-set VPN state without
/// performing any async operations or real connections.
class _FakeVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _FakeVpnConnectionNotifier(this._initialState);

  final VpnConnectionState _initialState;

  /// Tracks whether [connect] was called.
  bool connectCalled = false;
  ServerEntity? connectCalledWith;

  /// Tracks whether [disconnect] was called.
  bool disconnectCalled = false;

  @override
  Future<VpnConnectionState> build() async {
    return _initialState;
  }

  @override
  Future<void> connect(ServerEntity server) async {
    connectCalled = true;
    connectCalledWith = server;
  }

  @override
  Future<void> disconnect() async {
    disconnectCalled = true;
  }

  @override
  Future<void> handleNetworkChange(bool isOnline) async {}

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connectFromCustomServer(ImportedConfig customServer) async {}
}

// ---------------------------------------------------------------------------
// Fake VPN stats notifier
// ---------------------------------------------------------------------------

class _FakeVpnStatsNotifier extends Notifier<ConnectionStatsEntity?>
    implements VpnStatsNotifier {
  _FakeVpnStatsNotifier(this._initialState);

  final ConnectionStatsEntity? _initialState;

  @override
  ConnectionStatsEntity? build() => _initialState;
}

// ---------------------------------------------------------------------------
// Helper: build the widget under test with provider overrides
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required VpnConnectionState vpnState,
  ConnectionStatsEntity? stats,
  _FakeVpnConnectionNotifier? notifier,
}) {
  final connectionNotifier = notifier ??
      _FakeVpnConnectionNotifier(vpnState);

  return ProviderScope(
    overrides: [
      vpnConnectionProvider.overrideWith(
        () => connectionNotifier,
      ),
      vpnStatsProvider.overrideWith(
        () => _FakeVpnStatsNotifier(stats),
      ),
      // Override derived providers used by child widgets.
      currentServerProvider.overrideWith((ref) {
        final asyncState = ref.watch(vpnConnectionProvider);
        return asyncState.value?.server;
      }),
      activeProtocolProvider.overrideWith((ref) {
        final asyncState = ref.watch(vpnConnectionProvider);
        final value = asyncState.value;
        if (value is VpnConnected) return value.protocol;
        return null;
      }),
      isConnectedProvider.overrideWith((ref) {
        final asyncState = ref.watch(vpnConnectionProvider);
        return asyncState.value?.isConnected ?? false;
      }),
      currentSpeedProvider.overrideWith((ref) {
        final statsValue = ref.watch(vpnStatsProvider);
        if (statsValue == null) {
          return (download: '0 B/s', upload: '0 B/s');
        }
        return (download: '1.0 MB/s', upload: '512 KB/s');
      }),
      sessionUsageProvider.overrideWith((ref) {
        final statsValue = ref.watch(vpnStatsProvider);
        if (statsValue == null) {
          return (download: '0 B', upload: '0 B', total: '0 B');
        }
        return (download: '100 MB', upload: '50 MB', total: '150 MB');
      }),
      sessionDurationProvider.overrideWith((ref) {
        final statsValue = ref.watch(vpnStatsProvider);
        if (statsValue == null) return '0s';
        return '1h 30m';
      }),
    ],
    child: const MaterialApp(
      home: ConnectionScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Overflow error suppression (common in widget tests with constrained layout)
// ---------------------------------------------------------------------------

void ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final exception = details.exception;
    final isOverflow = exception is FlutterError &&
        exception.message.contains('overflowed');
    if (!isOverflow) {
      FlutterError.presentError(details);
    }
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(ignoreOverflowErrors);

  // =========================================================================
  // Group 1: Disconnected and Connecting states
  // =========================================================================

  group('ConnectionScreen - disconnected state', () {
    testWidgets('renders "Not Protected" status label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Not Protected'), findsOneWidget);
    });

    testWidgets('renders ConnectButton widget', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectButton), findsOneWidget);
    });

    testWidgets('renders "Connect" label on the button', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Connect'), findsOneWidget);
    });

    testWidgets('renders ConnectionInfo widget', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectionInfo), findsOneWidget);
    });

    testWidgets('renders SpeedIndicator widget', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(SpeedIndicator), findsOneWidget);
    });

    testWidgets('does not show error banner in disconnected state',
        (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Connection Error'), findsNothing);
    });

    testWidgets('shows "Select a server to connect" when no server selected',
        (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnected(),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Select a server to connect'), findsOneWidget);
    });
  });

  group('ConnectionScreen - connecting state', () {
    testWidgets('renders "Connecting..." status label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: VpnConnecting(server: _testServer),
      ));
      // Use pump() instead of pumpAndSettle() because the pulse animation
      // never settles.
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.text('Connecting...'), findsAtLeast(1));
    });

    testWidgets('renders the connecting button label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: VpnConnecting(server: _testServer),
      ));
      await tester.pump(const Duration(milliseconds: 500));

      // ConnectButton shows "Connecting..." in connecting state.
      expect(find.text('Connecting...'), findsAtLeast(1));
    });

    testWidgets('renders server name during connecting', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: VpnConnecting(server: _testServer),
      ));
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.text('US East 1'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 2: Connected state with speed stats
  // =========================================================================

  group('ConnectionScreen - connected state', () {
    final connectedState = VpnConnected(
      server: _testServer,
      protocol: VpnProtocol.vless,
    );

    final mockStats = createMockConnectionStats(
      downloadSpeed: 1024000,
      uploadSpeed: 512000,
      totalDownload: 104857600,
      totalUpload: 52428800,
      connectionDuration: const Duration(hours: 1, minutes: 30),
      serverName: 'US East 1',
      protocol: 'vless',
      ipAddress: '203.0.113.1',
    );

    testWidgets('renders "Protected" status label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      expect(find.text('Protected'), findsOneWidget);
    });

    testWidgets('renders "Connected" button label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      expect(find.text('Connected'), findsOneWidget);
    });

    testWidgets('renders server name', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      expect(find.text('US East 1'), findsOneWidget);
    });

    testWidgets('renders protocol chip', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      // VpnProtocol.vless displays as 'Reality' in the ProtocolChip.
      expect(find.text('Reality'), findsOneWidget);
    });

    testWidgets('renders speed stats', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      // SpeedIndicator labels.
      expect(find.text('Download'), findsOneWidget);
      expect(find.text('Upload'), findsOneWidget);
    });

    testWidgets('renders session duration', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      // The session duration label comes from BottomStatsSection.
      expect(find.text('Duration'), findsOneWidget);
      expect(find.text('1h 30m'), findsOneWidget);
    });

    testWidgets('renders data usage', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
      ));
      await tester.pumpAndSettle();

      expect(find.text('Data Used'), findsOneWidget);
      expect(find.text('150 MB'), findsOneWidget);
    });

    testWidgets('tap on connected button calls disconnect', (tester) async {
      final fakeNotifier = _FakeVpnConnectionNotifier(connectedState);

      await tester.pumpWidget(_buildTestWidget(
        vpnState: connectedState,
        stats: mockStats,
        notifier: fakeNotifier,
      ));
      await tester.pumpAndSettle();

      // Tap the connect button (which in connected state triggers disconnect).
      await tester.tap(find.byType(ConnectButton));
      await tester.pumpAndSettle();

      expect(fakeNotifier.disconnectCalled, isTrue);
    });
  });

  // =========================================================================
  // Group 3: Error state and retry functionality
  // =========================================================================

  group('ConnectionScreen - error state', () {
    testWidgets('renders "Connection Error" status label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnError(message: 'Network timeout'),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Connection Error'), findsOneWidget);
    });

    testWidgets('renders error message in banner', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnError(message: 'Network timeout'),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Network timeout'), findsOneWidget);
    });

    testWidgets('renders "Retry" button label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnError(message: 'Connection refused'),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('renders error icon in the banner', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnError(message: 'Server unreachable'),
      ));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('tap retry button calls connect with current server',
        (tester) async {
      // For retry to work, currentServerProvider must return a server.
      // We override it by providing a connected-then-error scenario where
      // the notifier has been set up with an error state but a server is
      // accessible via the provider.
      const errorState = VpnError(message: 'Timeout');
      final fakeNotifier = _FakeVpnConnectionNotifier(errorState);

      // Build widget with an extra override for currentServerProvider
      // to return _testServer even in error state.
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            vpnConnectionProvider.overrideWith(() => fakeNotifier),
            vpnStatsProvider.overrideWith(
              () => _FakeVpnStatsNotifier(null),
            ),
            currentServerProvider.overrideWith((ref) => _testServer),
            activeProtocolProvider.overrideWith((ref) => null),
            isConnectedProvider.overrideWith((ref) => false),
            currentSpeedProvider.overrideWith(
              (ref) => (download: '0 B/s', upload: '0 B/s'),
            ),
            sessionUsageProvider.overrideWith(
              (ref) =>
                  (download: '0 B', upload: '0 B', total: '0 B'),
            ),
            sessionDurationProvider.overrideWith((ref) => '0s'),
          ],
          child: const MaterialApp(
            home: ConnectionScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap the Retry button (the ConnectButton in error state).
      await tester.tap(find.byType(ConnectButton));
      await tester.pumpAndSettle();

      expect(fakeNotifier.connectCalled, isTrue);
      expect(fakeNotifier.connectCalledWith?.id, _testServer.id);
    });

    testWidgets('different error messages display correctly', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnError(message: 'Authentication failed'),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Authentication failed'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 4: Disconnecting and Reconnecting states
  // =========================================================================

  group('ConnectionScreen - transitional states', () {
    testWidgets('disconnecting state shows status label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: const VpnDisconnecting(),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Disconnecting...'), findsAtLeast(1));
    });

    testWidgets('reconnecting state shows status label', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        vpnState: VpnReconnecting(attempt: 1, server: _testServer),
      ));
      // Use pump() because reconnecting triggers pulse animation.
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.text('Reconnecting...'), findsAtLeast(1));
    });
  });
}
