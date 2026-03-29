import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/screens/connection_screen.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _smokeServer = ServerEntity(
  id: 'smoke-server',
  name: 'Smoke Server',
  countryCode: 'US',
  countryName: 'United States',
  city: 'New York',
  address: '203.0.113.1',
  port: 443,
  protocol: 'vless',
  isAvailable: true,
  ping: 25,
);

class _FakeVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _FakeVpnConnectionNotifier(this._initialState);

  final VpnConnectionState _initialState;

  @override
  Future<VpnConnectionState> build() async => _initialState;

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connect(ServerEntity server) async {}

  @override
  Future<void> connectFromCustomServer(ImportedConfig customServer) async {}

  @override
  Future<void> connectToLastOrRecommended() async {}

  @override
  Future<void> disconnect() async {}

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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Widget buildSubject({
    required VpnConnectionState vpnState,
    ConnectionStatsEntity? stats,
  }) {
    return ProviderScope(
      overrides: [
        vpnConnectionProvider.overrideWith(
          () => _FakeVpnConnectionNotifier(vpnState),
        ),
        vpnStatsProvider.overrideWith(() => _FakeVpnStatsNotifier(stats)),
        currentServerProvider.overrideWith((ref) => vpnState.server),
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
      child: const MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: Locale('en'),
        home: ConnectionScreen(),
      ),
    );
  }

  testWidgets('renders disconnected screen without throwing', (tester) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1080, 1920));

    await tester.pumpWidget(buildSubject(vpnState: const VpnDisconnected()));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Not Protected'), findsOneWidget);
    expect(find.text('Connect'), findsOneWidget);
  });

  testWidgets('renders connected summary without full-screen errors', (
    tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1080, 1920));

    await tester.pumpWidget(
      buildSubject(
        vpnState: const VpnConnected(
          server: _smokeServer,
          protocol: VpnProtocol.vless,
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Protected'), findsOneWidget);
    expect(find.text('Smoke Server'), findsOneWidget);
    expect(find.text('1h 30m'), findsWidgets);
    expect(find.text('150 MB'), findsOneWidget);
  });

  testWidgets('renders connected state on narrow viewport without overflow', (
    tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(360, 760));

    await tester.pumpWidget(
      buildSubject(
        vpnState: const VpnConnected(
          server: _smokeServer,
          protocol: VpnProtocol.vless,
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(ConnectionScreen), findsOneWidget);
    expect(find.byType(SpeedIndicator), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
