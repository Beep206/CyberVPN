import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/notification_prefs_screen.dart';

// ---------------------------------------------------------------------------
// Fake SettingsNotifier
// ---------------------------------------------------------------------------

/// A fake [SettingsNotifier] that holds an in-memory [AppSettings] without
/// touching SharedPreferences.
class _FakeSettingsNotifier extends AsyncNotifier<AppSettings>
    implements SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
      : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> toggleNotification(NotificationType type) async {
    _settings = switch (type) {
      NotificationType.connection => _settings.copyWith(
          notificationConnection: !_settings.notificationConnection,
        ),
      NotificationType.expiry => _settings.copyWith(
          notificationExpiry: !_settings.notificationExpiry,
        ),
      NotificationType.promotional => _settings.copyWith(
          notificationPromotional: !_settings.notificationPromotional,
        ),
      NotificationType.referral => _settings.copyWith(
          notificationReferral: !_settings.notificationReferral,
        ),
      NotificationType.vpnSpeed => _settings.copyWith(
          notificationVpnSpeed: !_settings.notificationVpnSpeed,
        ),
    };
    state = AsyncData(_settings);
  }

  // Stubs for the full interface -- not exercised in these tests.
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
  Future<void> updateProtocol(PreferredProtocol protocol) async {}
  @override
  Future<void> toggleAutoConnect() async {}
  @override
  Future<void> toggleAutoConnectUntrustedWifi() async {}
  @override
  Future<void> toggleKillSwitch() async {}
  @override
  Future<void> toggleSplitTunneling() async {}
  @override
  Future<void> updateMtu({required MtuMode mode, int? mtuValue}) async {}
  @override
  Future<void> updateDns({required DnsProvider provider, String? customDns}) async {}
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
      home: NotificationPrefsScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('NotificationPrefsScreen', () {
    testWidgets('renders screen title', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('Notification Preferences'), findsOneWidget);
    });

    testWidgets('renders all notification toggle tiles', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.text('Connection status changes'), findsOneWidget);
      expect(find.text('Subscription expiry'), findsOneWidget);
      expect(find.text('Promotional'), findsOneWidget);
      expect(find.text('Referral activity'), findsOneWidget);
      expect(find.text('Security alerts'), findsOneWidget);
    });

    testWidgets('toggle promotional updates provider from false to true',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Verify initially off (default for promotional is false).
      final switchFinder = find.byKey(const Key('toggle_notification_promotional'));
      expect(switchFinder, findsOneWidget);

      // Find the Switch widget within the promotional tile.
      final switches = find.descendant(
        of: switchFinder,
        matching: find.byType(Switch),
      );
      var switchWidget = tester.widget<Switch>(switches);
      expect(switchWidget.value, isFalse);

      // Tap to toggle on.
      await tester.tap(find.text('Promotional'));
      await tester.pumpAndSettle();

      // Verify provider state was updated.
      expect(notifier._settings.notificationPromotional, isTrue);

      // Verify the switch now shows true.
      switchWidget = tester.widget<Switch>(switches);
      expect(switchWidget.value, isTrue);
    });

    testWidgets('security alerts toggle is disabled (onChanged is null)',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Find the Switch inside the security alerts tile.
      final securityTile = find.byKey(const Key('toggle_notification_security'));
      expect(securityTile, findsOneWidget);

      final switchFinder = find.descendant(
        of: securityTile,
        matching: find.byType(Switch),
      );
      final switchWidget = tester.widget<Switch>(switchFinder);

      // Verify it is always on and disabled.
      expect(switchWidget.value, isTrue);
      expect(switchWidget.onChanged, isNull);
    });

    testWidgets('security alerts shows explanation subtitle', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(
        find.text('Required for account security. Cannot be disabled.'),
        findsOneWidget,
      );
    });

    testWidgets('connection toggle reflects default on state', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      final connectionTile = find.byKey(
        const Key('toggle_notification_connection'),
      );
      final switchFinder = find.descendant(
        of: connectionTile,
        matching: find.byType(Switch),
      );
      final switchWidget = tester.widget<Switch>(switchFinder);
      expect(switchWidget.value, isTrue);
    });

    testWidgets('referral toggle can be toggled off', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Initially on.
      expect(notifier._settings.notificationReferral, isTrue);

      // Tap to toggle off.
      await tester.tap(find.text('Referral activity'));
      await tester.pumpAndSettle();

      expect(notifier._settings.notificationReferral, isFalse);
    });

    // Note: The Android-only VPN speed toggle cannot be tested in standard
    // widget tests because Platform.isAndroid returns false in test
    // environments. The toggle is guarded by a try-catch that returns false
    // when Platform is unavailable, so it will not render in tests.
    testWidgets('VPN speed toggle is not shown in test environment',
        (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('toggle_notification_vpn_speed')),
        findsNothing,
      );
    });
  });
}
