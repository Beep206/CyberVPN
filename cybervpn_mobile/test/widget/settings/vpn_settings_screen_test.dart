import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/vpn_settings_screen.dart';

// ---------------------------------------------------------------------------
// Fake SettingsNotifier
// ---------------------------------------------------------------------------

/// A fake [SettingsNotifier] that holds an in-memory [AppSettings] and
/// records method calls for assertion purposes.
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
  Future<void> toggleSplitTunneling() async {
    _settings = _settings.copyWith(
      splitTunneling: !_settings.splitTunneling,
    );
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
  Future<void> updateDns({
    required DnsProvider provider,
    String? customDns,
  }) async {
    _settings = _settings.copyWith(
      dnsProvider: provider,
      customDns: customDns,
    );
    state = AsyncData(_settings);
  }

  // Stubs for methods not used in VPN settings tests.
  @override
  Future<void> updateThemeMode(AppThemeMode mode) async {}
  @override
  Future<void> updateBrightness(AppBrightness brightness) async {}
  @override
  Future<void> updateDynamicColor(bool enabled) async {}
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
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required _FakeSettingsNotifier notifier,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => notifier),
    ],
    child: const MaterialApp(
      home: VpnSettingsScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  // =========================================================================
  // Group 1: Basic rendering
  // =========================================================================

  group('VpnSettingsScreen - rendering', () {
    testWidgets('renders screen title', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('VPN Settings'), findsOneWidget);
    });

    testWidgets('renders all sections', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('Protocol Preference'), findsOneWidget);
      expect(find.text('Auto-Connect'), findsOneWidget);
      expect(find.text('Security'), findsOneWidget);
      expect(find.text('DNS Provider'), findsOneWidget);
      expect(find.text('Advanced'), findsOneWidget);
    });

    testWidgets('renders connection notice', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('Changes apply on next connection'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 2: Protocol selection
  // =========================================================================

  group('VpnSettingsScreen - protocol selection', () {
    testWidgets('renders all protocol options', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('radio_protocol_auto')), findsOneWidget);
      expect(find.byKey(const Key('radio_protocol_vlessReality')), findsOneWidget);
      expect(find.byKey(const Key('radio_protocol_vlessXhttp')), findsOneWidget);
      expect(find.byKey(const Key('radio_protocol_vlessWsTls')), findsOneWidget);
    });

    testWidgets('renders protocol labels', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('Auto'), findsOneWidget);
      expect(find.text('VLESS Reality'), findsOneWidget);
      expect(find.text('VLESS XHTTP'), findsOneWidget);
      expect(find.text('VLESS WS+TLS'), findsOneWidget);
    });

    testWidgets('tapping protocol radio updates provider', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Tap VLESS Reality.
      await tester.tap(find.text('VLESS Reality'));
      await tester.pumpAndSettle();

      expect(notifier._settings.preferredProtocol,
          equals(PreferredProtocol.vlessReality));
    });
  });

  // =========================================================================
  // Group 3: Auto-connect toggles
  // =========================================================================

  group('VpnSettingsScreen - auto-connect', () {
    testWidgets('auto-connect on launch toggle renders', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('toggle_auto_connect_launch')), findsOneWidget);
      expect(find.text('Auto-connect on launch'), findsOneWidget);
      expect(find.text('Connect to VPN when the app starts'), findsOneWidget);
    });

    testWidgets('auto-connect on untrusted WiFi toggle renders',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('toggle_auto_connect_wifi')), findsOneWidget);
      expect(find.text('Auto-connect on untrusted WiFi'), findsOneWidget);
    });

    testWidgets('tapping auto-connect launch toggle updates state',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Default is false.
      expect(notifier._settings.autoConnectOnLaunch, isFalse);

      // Tap the toggle.
      await tester.tap(find.text('Auto-connect on launch'));
      await tester.pumpAndSettle();

      expect(notifier._settings.autoConnectOnLaunch, isTrue);
    });

    testWidgets('tapping auto-connect WiFi toggle updates state',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(notifier._settings.autoConnectUntrustedWifi, isFalse);

      await tester.tap(find.text('Auto-connect on untrusted WiFi'));
      await tester.pumpAndSettle();

      expect(notifier._settings.autoConnectUntrustedWifi, isTrue);
    });
  });

  // =========================================================================
  // Group 4: Kill switch
  // =========================================================================

  group('VpnSettingsScreen - kill switch', () {
    testWidgets('kill switch toggle renders', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('toggle_kill_switch')), findsOneWidget);
      expect(find.text('Kill switch'), findsOneWidget);
      expect(
        find.text('Block traffic if VPN disconnects unexpectedly'),
        findsOneWidget,
      );
    });

    testWidgets('kill switch shows confirmation dialog before enabling',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Default kill switch is off. Tap to toggle on.
      await tester.tap(find.text('Kill switch'));
      await tester.pumpAndSettle();

      // Confirmation dialog should appear.
      expect(find.text('Enable Kill Switch?'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Enable'), findsOneWidget);
    });

    testWidgets('confirming kill switch dialog enables it', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(notifier._settings.killSwitch, isFalse);

      await tester.tap(find.text('Kill switch'));
      await tester.pumpAndSettle();

      // Tap Enable in the dialog.
      await tester.tap(find.text('Enable'));
      await tester.pumpAndSettle();

      expect(notifier._settings.killSwitch, isTrue);
    });

    testWidgets('cancelling kill switch dialog does not enable it',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Kill switch'));
      await tester.pumpAndSettle();

      // Tap Cancel in the dialog.
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(notifier._settings.killSwitch, isFalse);
    });
  });

  // =========================================================================
  // Group 5: Split tunneling
  // =========================================================================

  group('VpnSettingsScreen - split tunneling', () {
    testWidgets('split tunneling toggle renders', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('toggle_split_tunneling')), findsOneWidget);
      expect(find.text('Split tunneling'), findsOneWidget);
    });

    testWidgets('tapping split tunneling toggles state', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(notifier._settings.splitTunneling, isFalse);

      await tester.tap(find.text('Split tunneling'));
      await tester.pumpAndSettle();

      expect(notifier._settings.splitTunneling, isTrue);
    });
  });

  // =========================================================================
  // Group 6: DNS provider
  // =========================================================================

  group('VpnSettingsScreen - DNS provider', () {
    testWidgets('renders all DNS options', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('radio_dns_system')), findsOneWidget);
      expect(find.byKey(const Key('radio_dns_cloudflare')), findsOneWidget);
      expect(find.byKey(const Key('radio_dns_google')), findsOneWidget);
      expect(find.byKey(const Key('radio_dns_quad9')), findsOneWidget);
      expect(find.byKey(const Key('radio_dns_custom')), findsOneWidget);
    });

    testWidgets('renders DNS labels', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('System'), findsOneWidget);
      expect(find.text('Cloudflare (1.1.1.1)'), findsOneWidget);
      expect(find.text('Google (8.8.8.8)'), findsOneWidget);
      expect(find.text('Quad9 (9.9.9.9)'), findsOneWidget);
      expect(find.text('Custom'), findsOneWidget);
    });

    testWidgets('custom DNS input is hidden when System is selected',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('input_custom_dns')), findsNothing);
    });

    testWidgets('custom DNS input appears when Custom is selected',
        (tester) async {
      final notifier = _FakeSettingsNotifier(
        const AppSettings(dnsProvider: DnsProvider.custom),
      );

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('input_custom_dns')), findsOneWidget);
      expect(find.text('Custom DNS address'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 7: MTU configuration
  // =========================================================================

  group('VpnSettingsScreen - MTU', () {
    testWidgets('renders MTU auto and manual radio options', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('radio_mtu_auto')), findsOneWidget);
      expect(find.byKey(const Key('radio_mtu_manual')), findsOneWidget);
      expect(find.text('MTU: Auto'), findsOneWidget);
      expect(find.text('MTU: Manual'), findsOneWidget);
    });

    testWidgets('MTU input is hidden when Auto is selected', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('input_mtu_value')), findsNothing);
    });

    testWidgets('MTU input appears when Manual is selected', (tester) async {
      final notifier = _FakeSettingsNotifier(
        const AppSettings(mtuMode: MtuMode.manual),
      );

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('input_mtu_value')), findsOneWidget);
      expect(find.text('MTU value'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 8: Loading and error states
  // =========================================================================

  group('VpnSettingsScreen - loading/error', () {
    testWidgets('shows loading indicator when settings are loading',
        (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(_NeverCompleteSettingsNotifier.new),
          ],
          child: const MaterialApp(
            home: VpnSettingsScreen(),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows error state with retry button', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(_ErrorSettingsNotifier.new),
          ],
          child: const MaterialApp(
            home: VpnSettingsScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load settings'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });
}

// ---------------------------------------------------------------------------
// Helpers for loading and error states
// ---------------------------------------------------------------------------

class _NeverCompleteSettingsNotifier extends SettingsNotifier {
  @override
  Future<AppSettings> build() {
    return Future<AppSettings>.delayed(const Duration(days: 1));
  }
}

class _ErrorSettingsNotifier extends SettingsNotifier {
  @override
  Future<AppSettings> build() async {
    throw Exception('Test error');
  }
}
