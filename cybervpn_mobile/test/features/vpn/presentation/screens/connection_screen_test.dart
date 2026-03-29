import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/screens/connection_screen.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connect_button.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connection_info.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _testServer = ServerEntity(
  id: 'us-east-1',
  name: 'US East 1',
  countryCode: 'US',
  countryName: 'United States',
  city: 'New York',
  address: '203.0.113.10',
  port: 443,
  protocol: 'vless',
  isAvailable: true,
  ping: 25,
);

const _testStats = ConnectionStatsEntity(
  downloadSpeed: 1024000,
  uploadSpeed: 512000,
  totalDownload: 104857600,
  totalUpload: 52428800,
  connectionDuration: Duration(hours: 1, minutes: 30),
  serverName: 'US East 1',
  protocol: 'vless',
  ipAddress: '203.0.113.10',
);

class _FakeVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _FakeVpnConnectionNotifier(this._initialState);

  final VpnConnectionState _initialState;
  bool connectCalled = false;
  bool disconnectCalled = false;
  ServerEntity? connectedServer;

  @override
  Future<VpnConnectionState> build() async => _initialState;

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connect(ServerEntity server) async {
    connectCalled = true;
    connectedServer = server;
  }

  @override
  Future<void> connectFromCustomServer(ImportedConfig customServer) async {}

  @override
  Future<void> connectToLastOrRecommended() async {}

  @override
  Future<void> disconnect() async {
    disconnectCalled = true;
  }

  @override
  Future<void> handleNetworkChange(bool isOnline) async {}
}

class _FakeVpnStatsNotifier extends Notifier<ConnectionStatsEntity?>
    implements VpnStatsNotifier {
  _FakeVpnStatsNotifier(this._stats);

  final ConnectionStatsEntity? _stats;

  @override
  ConnectionStatsEntity? build() => _stats;
}

Widget _buildSubject({
  required VpnConnectionState vpnState,
  ConnectionStatsEntity? stats,
  _FakeVpnConnectionNotifier? notifier,
  ServerEntity? currentServer,
}) {
  final connectionNotifier = notifier ?? _FakeVpnConnectionNotifier(vpnState);

  return ProviderScope(
    overrides: [
      vpnConnectionProvider.overrideWith(() => connectionNotifier),
      vpnStatsProvider.overrideWith(() => _FakeVpnStatsNotifier(stats)),
      currentServerProvider.overrideWith(
        (ref) => currentServer ?? vpnState.server,
      ),
      activeProtocolProvider.overrideWith((ref) {
        if (vpnState is VpnConnected) {
          return vpnState.protocol;
        }
        return null;
      }),
      isConnectedProvider.overrideWith((ref) => vpnState.isConnected),
      currentSpeedProvider.overrideWith(
        (ref) => (download: '1.0 MB/s', upload: '512 KB/s'),
      ),
      sessionUsageProvider.overrideWith(
        (ref) => (download: '100 MB', upload: '50 MB', total: '150 MB'),
      ),
      sessionDurationProvider.overrideWith((ref) => '1h 30m'),
      activeVpnProfileProvider.overrideWith(
        (ref) => Stream<VpnProfile?>.value(null),
      ),
      profileListProvider.overrideWith(
        (ref) => Stream<List<VpnProfile>>.value(const []),
      ),
    ],
    child: const MediaQuery(
      data: MediaQueryData(size: Size(1080, 1920), disableAnimations: true),
      child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: Locale('en'),
        home: ConnectionScreen(),
      ),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('disconnected state renders core widgets', (tester) async {
    await tester.pumpWidget(_buildSubject(vpnState: const VpnDisconnected()));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Not Protected'), findsOneWidget);
    expect(find.text('Connect'), findsOneWidget);
    expect(find.byType(ConnectButton), findsOneWidget);
    expect(find.byType(ConnectionInfo), findsOneWidget);
    expect(find.byType(SpeedIndicator), findsOneWidget);
    expect(find.text('Select a server to connect'), findsOneWidget);
  });

  testWidgets('connecting state renders status and current server', (
    tester,
  ) async {
    await tester.pumpWidget(
      _buildSubject(vpnState: const VpnConnecting(server: _testServer)),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Connecting...'), findsWidgets);
    expect(find.text('US East 1'), findsOneWidget);
  });

  testWidgets('connected state renders summary stats', (tester) async {
    await tester.pumpWidget(
      _buildSubject(
        vpnState: const VpnConnected(
          server: _testServer,
          protocol: VpnProtocol.vless,
        ),
        stats: _testStats,
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Protected'), findsOneWidget);
    expect(find.text('Connected'), findsOneWidget);
    expect(find.text('US East 1'), findsOneWidget);
    expect(find.text('Reality'), findsOneWidget);
    expect(find.text('Duration'), findsOneWidget);
    expect(find.text('Data Used'), findsOneWidget);
    expect(find.text('150 MB'), findsOneWidget);
  });

  testWidgets('connected state tap disconnect calls notifier', (tester) async {
    final notifier = _FakeVpnConnectionNotifier(
      const VpnConnected(server: _testServer, protocol: VpnProtocol.vless),
    );

    await tester.pumpWidget(
      _buildSubject(
        vpnState: const VpnConnected(
          server: _testServer,
          protocol: VpnProtocol.vless,
        ),
        stats: _testStats,
        notifier: notifier,
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    await tester.tap(find.byType(ConnectButton));
    await tester.pump();

    expect(notifier.disconnectCalled, isTrue);
  });

  testWidgets('error state renders banner and retry action', (tester) async {
    final notifier = _FakeVpnConnectionNotifier(
      const VpnError(message: 'Network timeout'),
    );

    await tester.pumpWidget(
      _buildSubject(
        vpnState: const VpnError(message: 'Network timeout'),
        stats: _testStats,
        notifier: notifier,
        currentServer: _testServer,
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Connection Error'), findsOneWidget);
    expect(find.text('Network timeout'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);

    await tester.tap(find.byType(ConnectButton));
    await tester.pump();

    expect(notifier.connectCalled, isTrue);
    expect(notifier.connectedServer?.id, _testServer.id);
  });

  testWidgets('transitional states render expected labels', (tester) async {
    await tester.pumpWidget(_buildSubject(vpnState: const VpnDisconnecting()));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Disconnecting...'), findsWidgets);

    await tester.pumpWidget(
      _buildSubject(
        vpnState: const VpnReconnecting(attempt: 1, server: _testServer),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byType(ConnectionScreen), findsOneWidget);
    expect(find.byType(ConnectButton), findsOneWidget);
  });
}
