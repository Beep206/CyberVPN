import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/settings/data/datasources/android_system_integration_service.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/android_system_integration_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/vpn_general_settings_screen.dart';

class _FakeSettingsNotifier extends AsyncNotifier<AppSettings>
    implements SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> updateProtocol(PreferredProtocol protocol) async {
    _settings = _settings.copyWith(preferredProtocol: protocol);
    state = AsyncData(_settings);
  }

  @override
  Future<void> toggleAutoConnect() async {
    _settings = _settings.copyWith(
      autoConnectOnLaunch: !_settings.autoConnectOnLaunch,
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> toggleAutoConnectUntrustedWifi() async {
    _settings = _settings.copyWith(
      autoConnectUntrustedWifi: !_settings.autoConnectUntrustedWifi,
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> toggleKillSwitch() async {
    _settings = _settings.copyWith(killSwitch: !_settings.killSwitch);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateDns({
    required DnsProvider provider,
    String? customDns,
  }) async {
    _settings = _settings.copyWith(dnsProvider: provider, customDns: customDns);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateMtu({required MtuMode mode, int? mtuValue}) async {
    _settings = _settings.copyWith(
      mtuMode: mode,
      mtuValue: mtuValue ?? _settings.mtuValue,
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateUseDnsFromJson(bool enabled) async {
    _settings = _settings.copyWith(useDnsFromJson: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateLocalDnsSettings({
    required bool enabled,
    int? port,
  }) async {
    _settings = _settings.copyWith(
      useLocalDns: enabled,
      localDnsPort: port ?? _settings.localDnsPort,
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateServerAddressResolve({
    required bool enabled,
    String? dohUrl,
    String? dnsIp,
  }) async {
    _settings = _settings.copyWith(
      serverAddressResolveEnabled: enabled,
      serverAddressResolveDohUrl: dohUrl,
      serverAddressResolveDnsIp: dnsIp,
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> updatePingSettings({
    required PingMode mode,
    String? pingTestUrl,
  }) async {}

  @override
  Future<void> updatePingDisplayMode(PingDisplayMode displayMode) async {}

  @override
  Future<void> updatePingResultMode(PingResultMode resultMode) async {}

  @override
  Future<void> updateRoutingEnabled(bool enabled) async {}

  @override
  Future<void> replaceRoutingProfiles(List<RoutingProfile> profiles) async {}

  @override
  Future<void> upsertRoutingProfile(RoutingProfile profile) async {}

  @override
  Future<void> removeRoutingProfile(String profileId) async {}

  @override
  Future<void> setActiveRoutingProfile(String? profileId) async {}

  @override
  Future<void> updateBypassSubnets(List<String> subnets) async {}

  @override
  Future<void> updateExcludedRouteEntries(
    List<ExcludedRouteEntry> entries,
  ) async {}

  @override
  Future<void> updatePerAppProxyMode(PerAppProxyMode mode) async {}

  @override
  Future<void> setPerAppProxyAppIds(List<String> appIds) async {}

  @override
  Future<void> togglePerAppProxyApp(String appId) async {}

  @override
  Future<void> toggleSplitTunneling() async {}

  @override
  Future<void> updateFragmentation(bool enabled) async {}

  @override
  Future<void> updateMux(bool enabled) async {}

  @override
  Future<void> updatePreferredIpType(PreferredIpType ipType) async {}

  @override
  Future<void> updateSniffing(bool enabled) async {}

  @override
  Future<void> updateVpnRunMode(VpnRunMode mode) async {}

  @override
  Future<void> updateSubscriptionSettings({
    bool? autoUpdateEnabled,
    int? autoUpdateIntervalHours,
    bool? updateNotificationsEnabled,
    bool? autoUpdateOnOpen,
    bool? pingOnOpenEnabled,
    SubscriptionConnectStrategy? connectStrategy,
    bool? preventDuplicateImports,
    bool? collapseSubscriptions,
    bool? noFilter,
    SubscriptionSortMode? sortMode,
  }) async {}

  @override
  Future<void> updateSubscriptionUserAgent({
    required SubscriptionUserAgentMode mode,
    String? value,
  }) async {}

  @override
  Future<void> updateAllowLanConnections(bool enabled) async {
    _settings = _settings.copyWith(allowLanConnections: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateAppAutoStart(bool enabled) async {
    _settings = _settings.copyWith(appAutoStart: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateThemeMode(AppThemeMode mode) async {}

  @override
  Future<void> updateBrightness(AppBrightness brightness) async {}

  @override
  Future<void> updateDynamicColor(bool enabled) async {}

  @override
  Future<void> updateOledMode(bool enabled) async {}

  @override
  Future<void> updateScanlineEffect(bool enabled) async {}

  @override
  Future<void> updateTextScale(TextScale scale) async {}

  @override
  Future<void> updateLocale(String locale) async {}

  @override
  Future<void> toggleNotification(NotificationType type) async {}

  @override
  Future<void> addTrustedNetwork(String ssid) async {}

  @override
  Future<void> removeTrustedNetwork(String ssid) async {}

  @override
  bool isTrustedNetwork(String ssid) => false;

  @override
  Future<void> clearTrustedNetworks() async {}

  @override
  Future<void> resetAll() async {}

  @override
  Future<bool> retryLastOperation() async => false;

  @override
  Future<void> validateConsistency() async {}

  @override
  Future<void> toggleClipboardAutoDetect() async {}

  @override
  Future<void> updateLogLevel(LogLevel level) async {}

  @override
  Future<void> updatePreferMapView(bool prefer) async {}
}

VpnSettingsSupportMatrix _androidSupportMatrix() {
  return VpnSettingsSupportMatrix.fromCapabilities(
    platform: VpnSettingsPlatform.android,
    supportsPerAppProxy: true,
    supportsExcludedRoutes: true,
    supportsLocalDns: false,
    supportsServerResolve: true,
    supportsSniffing: true,
    supportsProxyOnlyMode: true,
    supportsFragmentation: true,
    supportsMux: true,
    supportsPreferredIpType: true,
    supportsManualMtu: true,
  );
}

VpnSettingsSupportMatrix _iosSupportMatrix() {
  return VpnSettingsSupportMatrix.fromCapabilities(
    platform: VpnSettingsPlatform.ios,
    supportsPerAppProxy: false,
    supportsExcludedRoutes: false,
    supportsLocalDns: false,
    supportsServerResolve: true,
    supportsSniffing: true,
    supportsProxyOnlyMode: false,
    supportsFragmentation: true,
    supportsMux: true,
    supportsPreferredIpType: true,
    supportsManualMtu: false,
  );
}

class _FakeAndroidSystemIntegrationService
    implements AndroidSystemIntegrationService {
  bool syncedAutoStartValue = false;
  int syncCallCount = 0;

  @override
  bool get isSupported => true;

  @override
  Future<LanProxyStatus> readLanProxyStatus({required bool enabled}) async {
    return LanProxyStatus(
      isSupported: true,
      enabled: enabled,
      socksPort: 10807,
      httpPort: 10808,
      wifiIpv4: '192.168.1.20',
      wifiIpv6: 'fe80::1',
    );
  }

  @override
  Future<AppAutoStartStatus> readAppAutoStartStatus({
    required bool enabled,
  }) async {
    return AppAutoStartStatus(
      isSupported: true,
      enabled: enabled,
      bootReceiverReady: enabled,
      oemSettingsAvailable: true,
      batteryOptimizationIgnored: false,
      manufacturer: 'xiaomi',
      lastBootHandledAt: DateTime(2026, 4, 17, 9, 30),
    );
  }

  @override
  Future<void> syncAppAutoStartPreference(bool enabled) async {
    syncedAutoStartValue = enabled;
    syncCallCount++;
  }

  @override
  Future<bool> openAppAutoStartSettings() async => true;

  @override
  Future<bool> openBatteryOptimizationSettings() async => true;
}

class _UnsupportedAndroidSystemIntegrationService
    implements AndroidSystemIntegrationService {
  @override
  bool get isSupported => false;

  @override
  Future<LanProxyStatus> readLanProxyStatus({required bool enabled}) async {
    return LanProxyStatus.unsupported(enabled: enabled);
  }

  @override
  Future<AppAutoStartStatus> readAppAutoStartStatus({
    required bool enabled,
  }) async {
    return AppAutoStartStatus.unsupported(enabled: enabled);
  }

  @override
  Future<void> syncAppAutoStartPreference(bool enabled) async {}

  @override
  Future<bool> openAppAutoStartSettings() async => false;

  @override
  Future<bool> openBatteryOptimizationSettings() async => false;
}

Widget _buildTestWidget({
  required _FakeSettingsNotifier notifier,
  required VpnSettingsSupportMatrix supportMatrix,
  AndroidSystemIntegrationService? androidSystemIntegrationService,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => notifier),
      vpnSettingsSupportMatrixProvider.overrideWithValue(supportMatrix),
      androidSystemIntegrationServiceProvider.overrideWithValue(
        androidSystemIntegrationService ??
            (supportMatrix.platform == VpnSettingsPlatform.android
                ? _FakeAndroidSystemIntegrationService()
                : _UnsupportedAndroidSystemIntegrationService()),
      ),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: MediaQuery(
        data: MediaQueryData(size: Size(1080, 2400)),
        child: VpnGeneralSettingsScreen(),
      ),
    ),
  );
}

void _setLargeSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
}

void main() {
  group('VpnGeneralSettingsScreen', () {
    testWidgets('renders protocol, DNS, and MTU sections', (tester) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Protocol Preference'), findsOneWidget);
      expect(find.text('Auto Connect'), findsOneWidget);
      expect(find.text('Security'), findsOneWidget);
      await tester.scrollUntilVisible(find.text('MTU'), 300);

      expect(find.byKey(const Key('radio_dns_system')), findsOneWidget);
      expect(find.text('MTU'), findsOneWidget);
    });

    testWidgets('updates DNS-from-JSON and server resolve settings', (
      tester,
    ) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.byKey(const Key('toggle_use_dns_from_json')),
        300,
      );
      await tester.ensureVisible(
        find.byKey(const Key('toggle_use_dns_from_json')),
      );
      await tester.tap(find.byKey(const Key('toggle_use_dns_from_json')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.byKey(const Key('toggle_server_address_resolve')),
      );
      await tester.tap(find.byKey(const Key('toggle_server_address_resolve')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.byKey(const Key('input_server_resolve_doh_url')),
      );
      await tester.enterText(
        find.byKey(const Key('input_server_resolve_doh_url')),
        'https://dns.google/resolve',
      );
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      expect(notifier._settings.useDnsFromJson, isTrue);
      expect(notifier._settings.serverAddressResolveEnabled, isTrue);
      expect(
        notifier._settings.serverAddressResolveDohUrl,
        'https://dns.google/resolve',
      );
    });

    testWidgets('updates protocol selection', (tester) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('radio_protocol_vlessReality')));
      await tester.pumpAndSettle();

      expect(
        notifier._settings.preferredProtocol,
        PreferredProtocol.vlessReality,
      );
    });

    testWidgets('shows custom DNS input when custom provider selected', (
      tester,
    ) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier(
        const AppSettings(dnsProvider: DnsProvider.custom),
      );

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.byKey(const Key('input_custom_dns')));

      expect(find.byKey(const Key('input_custom_dns')), findsOneWidget);
    });

    testWidgets('hides manual MTU option on iOS matrix', (tester) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier(
        const AppSettings(mtuMode: MtuMode.manual),
      );

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _iosSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('radio_mtu_manual')), findsNothing);
      expect(find.byKey(const Key('input_mtu_value')), findsNothing);
      await tester.scrollUntilVisible(
        find.byKey(const Key('vpn_general_mtu_notice')),
        300,
      );

      expect(find.byKey(const Key('vpn_general_mtu_notice')), findsOneWidget);
      expect(
        find.byKey(const Key('info_local_dns_unavailable')),
        findsOneWidget,
      );
    });

    testWidgets('renders and updates LAN + app auto-start sections', (
      tester,
    ) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();
      final androidSystem = _FakeAndroidSystemIntegrationService();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
          androidSystemIntegrationService: androidSystem,
        ),
      );
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.byKey(const Key('toggle_allow_lan_connections')),
        300,
      );
      await tester.tap(find.byKey(const Key('toggle_allow_lan_connections')));
      await tester.pumpAndSettle();

      expect(notifier._settings.allowLanConnections, isTrue);
      expect(find.byKey(const Key('info_allow_lan_socks_port')), findsOneWidget);

      await tester.scrollUntilVisible(
        find.byKey(const Key('toggle_app_auto_start')),
        300,
      );
      await tester.tap(find.byKey(const Key('toggle_app_auto_start')));
      await tester.pumpAndSettle();

      expect(notifier._settings.appAutoStart, isTrue);
      expect(androidSystem.syncedAutoStartValue, isTrue);
      expect(androidSystem.syncCallCount, 1);
      expect(find.byKey(const Key('nav_app_auto_start_settings')), findsOneWidget);
      expect(
        find.byKey(const Key('nav_battery_optimization_settings')),
        findsOneWidget,
      );
    });
  });
}
