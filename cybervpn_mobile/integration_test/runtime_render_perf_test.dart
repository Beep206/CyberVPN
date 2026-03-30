import 'dart:async';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/constants/onboarding_pages.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_list_screen.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_map_screen.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/speedometer_gauge.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connection_info.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _PerfTestApp extends StatelessWidget {
  const _PerfTestApp({required this.child, required this.overrides});

  final Widget child;
  final List<dynamic> overrides;

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      overrides: overrides.cast(),
      child: MaterialApp(
        home: child,
        locale: const Locale('en'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}

class _PerfServerListNotifier extends AsyncNotifier<ServerListState>
    implements ServerListNotifier {
  _PerfServerListNotifier(this._initialState);

  final ServerListState _initialState;

  @override
  Future<ServerListState> build() async => _initialState;

  @override
  Future<void> fetchServers() async {}

  @override
  void filterByCountry(String? countryCode) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData(current.copyWith(filterCountry: countryCode));
  }

  @override
  void filterByProtocol(dynamic protocol) {}

  @override
  Future<void> loadMore() async {}

  @override
  Future<void> refresh() async {}

  @override
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {}

  @override
  void sortBy(SortMode mode) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData(current.copyWith(sortMode: mode));
  }

  @override
  Future<void> toggleFavorite(String serverId) async {
    final current = state.value;
    if (current == null) return;

    final updatedServers = current.servers
        .map((server) {
          if (server.id == serverId) {
            return server.copyWith(isFavorite: !server.isFavorite);
          }
          return server;
        })
        .toList(growable: false);

    final favoriteIds = List<String>.from(current.favoriteServerIds);
    if (favoriteIds.contains(serverId)) {
      favoriteIds.remove(serverId);
    } else {
      favoriteIds.add(serverId);
    }

    state = AsyncData(
      current.copyWith(servers: updatedServers, favoriteServerIds: favoriteIds),
    );
  }
}

class _PerfSettingsNotifier extends SettingsNotifier {
  _PerfSettingsNotifier(this._settings);

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

class _PerfOnboardingRepository implements OnboardingRepository {
  @override
  Future<void> completeOnboarding() async {}

  @override
  Future<List<OnboardingPage>> getPages() async => getDefaultOnboardingPages();

  @override
  Future<bool> hasCompletedOnboarding() async => false;
}

class _PerfVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _PerfVpnConnectionNotifier(this._initialState);

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

class _PerfVpnStatsNotifier extends Notifier<ConnectionStatsEntity?>
    implements VpnStatsNotifier {
  _PerfVpnStatsNotifier(this._initialStats);

  final ConnectionStatsEntity? _initialStats;

  @override
  ConnectionStatsEntity? build() => _initialStats;

  void setStats(ConnectionStatsEntity? next) {
    state = next;
  }
}

List<ServerEntity> _buildPerfServers({int count = 160}) {
  const seeds = [
    ('US', 'United States', 'New York', 'vless'),
    ('DE', 'Germany', 'Frankfurt', 'vmess'),
    ('JP', 'Japan', 'Tokyo', 'trojan'),
    ('NL', 'Netherlands', 'Amsterdam', 'vless'),
    ('SG', 'Singapore', 'Singapore', 'shadowsocks'),
    ('GB', 'United Kingdom', 'London', 'vless'),
    ('CA', 'Canada', 'Toronto', 'vmess'),
    ('AU', 'Australia', 'Sydney', 'trojan'),
  ];

  return List<ServerEntity>.generate(count, (index) {
    final seed = seeds[index % seeds.length];
    final countryCode = seed.$1;
    final countryName = seed.$2;
    final city = seed.$3;
    final protocol = seed.$4;
    return ServerEntity(
      id: 'perf-server-$index',
      name: '$city ${index + 1}',
      countryCode: countryCode,
      countryName: countryName,
      city: city,
      address: '203.0.113.${(index % 200) + 1}',
      port: 443,
      protocol: protocol,
      ping: 18 + ((index * 7) % 180),
      load: 0.1 + ((index % 8) * 0.08),
      isFavorite: index < 6,
    );
  });
}

ConnectionStatsEntity _statsAt(int tick) {
  return ConnectionStatsEntity(
    downloadSpeed: 800000 + (tick * 70000),
    uploadSpeed: 350000 + (tick * 35000),
    totalDownload: 120000000 + (tick * 5000000),
    totalUpload: 64000000 + (tick * 2500000),
    connectionDuration: Duration(minutes: 8, seconds: tick),
    serverName: 'US East 1',
    protocol: 'vless',
    ipAddress: '203.0.113.10',
  );
}

Widget _buildConnectedSessionHarness(
  _PerfVpnConnectionNotifier connectionNotifier,
  _PerfVpnStatsNotifier statsNotifier,
) {
  return ProviderScope(
    overrides: [
      vpnConnectionProvider.overrideWith(() => connectionNotifier),
      vpnStatsProvider.overrideWith(() => statsNotifier),
      activeVpnProfileProvider.overrideWith((ref) => Stream.value(null)),
      profileListProvider.overrideWith(
        (ref) => Stream<List<VpnProfile>>.value(const <VpnProfile>[]),
      ),
    ],
    child: const MediaQuery(
      data: MediaQueryData(size: Size(430, 932), disableAnimations: true),
      child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: Locale('en'),
        home: Scaffold(
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ConnectionInfo(),
                SizedBox(height: 24),
                SpeedIndicator(),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

Map<String, dynamic> _summary(
  IntegrationTestWidgetsFlutterBinding binding,
  String reportKey,
) {
  final report = binding.reportData?[reportKey];
  expect(
    report,
    isA<Map<String, dynamic>>(),
    reason: '$reportKey summary missing',
  );
  final summary = Map<String, dynamic>.from(report! as Map<String, dynamic>);
  expect(
    summary['frame_count'],
    greaterThan(0),
    reason: '$reportKey produced no frames',
  );
  debugPrint(
    'PERF[$reportKey] '
    'frames=${summary['frame_count']} '
    'avg_build=${summary['average_frame_build_time_millis']}ms '
    'p90_build=${summary['90th_percentile_frame_build_time_millis']}ms '
    'avg_raster=${summary['average_frame_rasterizer_time_millis']}ms '
    'p90_raster=${summary['90th_percentile_frame_rasterizer_time_millis']}ms '
    'missed_build=${summary['missed_frame_build_budget_count']} '
    'missed_raster=${summary['missed_frame_rasterizer_budget_count']} '
    'new_gc=${summary['new_gen_gc_count']} '
    'old_gc=${summary['old_gen_gc_count']}',
  );
  return summary;
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Runtime render perf', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      prefs = await SharedPreferences.getInstance();
      await prefs.clear();
    });

    tearDown(() async {
      await prefs.clear();
    });

    testWidgets('server list scroll profile', (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(430, 932));

      final servers = _buildPerfServers();
      final state = ServerListState(
        servers: servers,
        favoriteServerIds: servers.take(6).map((server) => server.id).toList(),
      );

      await tester.pumpWidget(
        _PerfTestApp(
          overrides: <dynamic>[
            serverListProvider.overrideWith(
              () => _PerfServerListNotifier(state),
            ),
            sharedPreferencesProvider.overrideWithValue(prefs),
            importedConfigsProvider.overrideWith((ref) => const []),
            activeVpnProfileProvider.overrideWith((ref) => Stream.value(null)),
            settingsProvider.overrideWith(
              () => _PerfSettingsNotifier(const AppSettings()),
            ),
          ],
          child: const ServerListScreen(),
        ),
      );
      await tester.pumpAndSettle();

      await binding.watchPerformance(() async {
        await tester.drag(
          find.byType(CustomScrollView),
          const Offset(0, -1400),
        );
        await tester.pump(const Duration(milliseconds: 180));
        await tester.drag(
          find.byType(CustomScrollView),
          const Offset(0, -1400),
        );
        await tester.pump(const Duration(milliseconds: 180));
        await tester.drag(find.byType(CustomScrollView), const Offset(0, 1200));
        await tester.pump(const Duration(milliseconds: 180));
      }, reportKey: 'server_list_scroll');

      _summary(binding, 'server_list_scroll');
    });

    testWidgets('onboarding swipe profile', (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(430, 932));

      await tester.pumpWidget(
        _PerfTestApp(
          overrides: <dynamic>[
            onboardingRepositoryProvider.overrideWithValue(
              _PerfOnboardingRepository(),
            ),
          ],
          child: const OnboardingScreen(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 600));

      await binding.watchPerformance(() async {
        for (var i = 0; i < 3; i++) {
          await tester.drag(find.byType(PageView), const Offset(-800, 0));
          await tester.pump(const Duration(milliseconds: 450));
        }
      }, reportKey: 'onboarding_swipe');

      _summary(binding, 'onboarding_swipe');
    });

    testWidgets('server map interaction profile', (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(1280, 800));

      final servers = _buildPerfServers(count: 64);
      final state = ServerListState(servers: servers);

      await tester.pumpWidget(
        _PerfTestApp(
          overrides: <dynamic>[
            serverListProvider.overrideWith(
              () => _PerfServerListNotifier(state),
            ),
            activeVpnProfileProvider.overrideWith((ref) => Stream.value(null)),
          ],
          child: const SizedBox.expand(child: ServerMapScreen()),
        ),
      );
      await tester.pumpAndSettle();

      await binding.watchPerformance(() async {
        await tester.drag(find.byType(FlutterMap), const Offset(-260, 0));
        await tester.pumpAndSettle();
        await tester.drag(find.byType(FlutterMap), const Offset(180, -120));
        await tester.pumpAndSettle();
        final marker = find.byKey(
          const ValueKey<String>('server-map-country-US'),
        );
        if (marker.evaluate().isNotEmpty) {
          await tester.tap(marker);
          await tester.pump(const Duration(milliseconds: 180));
          final bottomSheet = find.text('United States');
          expect(bottomSheet, findsOneWidget);
        }
      }, reportKey: 'server_map_interaction');

      _summary(binding, 'server_map_interaction');
    });

    testWidgets('speedometer animation profile', (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(430, 932));

      Future<void> pumpGauge(double speed) {
        return tester.pumpWidget(
          const _PerfTestApp(
            overrides: <dynamic>[],
            child: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 280,
                  height: 280,
                  child: SpeedometerGauge(speed: 0),
                ),
              ),
            ),
          ),
        );
      }

      await pumpGauge(0);
      await tester.pump(const Duration(milliseconds: 16));

      await binding.watchPerformance(() async {
        for (var tick = 1; tick <= 24; tick++) {
          await tester.pumpWidget(
            _PerfTestApp(
              overrides: const <dynamic>[],
              child: Scaffold(
                body: Center(
                  child: SizedBox(
                    width: 280,
                    height: 280,
                    child: SpeedometerGauge(
                      speed: (tick * 4).toDouble(),
                      animationDuration: const Duration(milliseconds: 120),
                    ),
                  ),
                ),
              ),
            ),
          );
          await tester.pump(const Duration(milliseconds: 140));
        }
      }, reportKey: 'speedometer_animation');

      _summary(binding, 'speedometer_animation');
    });

    testWidgets('vpn connected long-session profile', (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(430, 932));

      const server = ServerEntity(
        id: 'us-east-1',
        name: 'US East 1',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '203.0.113.10',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        ping: 24,
      );

      final connectionNotifier = _PerfVpnConnectionNotifier(
        const VpnConnected(server: server, protocol: VpnProtocol.vless),
      );
      final statsNotifier = _PerfVpnStatsNotifier(_statsAt(0));

      await tester.pumpWidget(
        _buildConnectedSessionHarness(connectionNotifier, statsNotifier),
      );
      await tester.pumpAndSettle();

      await binding.watchPerformance(() async {
        for (var tick = 1; tick <= 48; tick++) {
          statsNotifier.setStats(_statsAt(tick));
          await tester.pump(const Duration(milliseconds: 120));
        }
      }, reportKey: 'vpn_connected_long_session');

      _summary(binding, 'vpn_connected_long_session');
    });
  });
}
