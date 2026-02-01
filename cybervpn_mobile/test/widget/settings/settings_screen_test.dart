import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/settings_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';

// ---------------------------------------------------------------------------
// Fake SettingsNotifier
// ---------------------------------------------------------------------------

/// A fake [SettingsNotifier] that holds an in-memory [AppSettings] without
/// touching SharedPreferences.
class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
      : _settings = initial ?? const AppSettings();

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  AppSettings settings = const AppSettings(),
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
    ],
    child: const MaterialApp(
      home: SettingsScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('SettingsScreen', () {
    testWidgets('renders Settings title in AppBar', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Settings'), findsOneWidget);
    });

    testWidgets('renders all settings sections', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // There should be 7 SettingsSection widgets.
      expect(find.byType(SettingsSection), findsNWidgets(7));

      // Verify section titles.
      expect(find.text('VPN Settings'), findsAtLeast(1));
      expect(find.text('Appearance'), findsAtLeast(1));
      expect(find.text('Language'), findsAtLeast(1));
      expect(find.text('Notifications'), findsAtLeast(1));
      expect(find.text('Account & Security'), findsAtLeast(1));
      expect(find.text('About'), findsOneWidget);
      expect(find.text('Debug & Diagnostics'), findsOneWidget);
    });

    testWidgets('VPN Settings tile shows current protocol', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(preferredProtocol: PreferredProtocol.vlessReality),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('VLESS Reality'), findsOneWidget);
    });

    testWidgets('VPN Settings tile shows Auto for default protocol',
        (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Default protocol is auto.
      expect(find.text('Auto'), findsOneWidget);
    });

    testWidgets('Appearance tile shows theme and brightness', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(
            themeMode: AppThemeMode.materialYou,
            brightness: AppBrightness.dark,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Material You / Dark'), findsOneWidget);
    });

    testWidgets('Appearance tile shows default Cyberpunk / System',
        (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Cyberpunk / System'), findsOneWidget);
    });

    testWidgets('Language tile shows current locale name', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(settings: const AppSettings(locale: 'ru')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Russian'), findsOneWidget);
    });

    testWidgets('Language tile shows English for default locale',
        (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('English'), findsOneWidget);
    });

    testWidgets('Notifications tile shows enabled count', (tester) async {
      // Default: connection=true, expiry=true, promotional=false, referral=true
      // => 3 of 4 enabled.
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('3 of 4 enabled'), findsOneWidget);
    });

    testWidgets('Notifications tile shows 0 when all disabled', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(
            notificationConnection: false,
            notificationExpiry: false,
            notificationPromotional: false,
            notificationReferral: false,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('0 of 4 enabled'), findsOneWidget);
    });

    testWidgets('Account & Security tile shows subtitle', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Profile, password, 2FA'), findsOneWidget);
    });

    testWidgets('About section shows version', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Version'), findsOneWidget);
      expect(find.text('1.0.0'), findsOneWidget);
    });

    testWidgets('About section shows legal tiles', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Open-source licenses'), findsOneWidget);
      expect(find.text('Terms of Service'), findsOneWidget);
      expect(find.text('Privacy Policy'), findsOneWidget);
    });

    testWidgets('all navigation tiles have chevron icon', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // The SettingsScreen has 8 navigation tiles:
      // VPN, Appearance, Language, Notifications, Account & Security,
      // Open-source licenses, Terms of Service, Privacy Policy, Debug = 9 tiles.
      // But "Version" is an info tile (no chevron). So 9 chevrons total.
      expect(find.byIcon(Icons.chevron_right), findsNWidgets(9));
    });

    testWidgets('all tiles have a key assigned', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('tile_vpn_settings')), findsOneWidget);
      expect(find.byKey(const Key('tile_appearance')), findsOneWidget);
      expect(find.byKey(const Key('tile_language')), findsOneWidget);
      expect(find.byKey(const Key('tile_notifications')), findsOneWidget);
      expect(find.byKey(const Key('tile_account_security')), findsOneWidget);
      expect(find.byKey(const Key('tile_about_version')), findsOneWidget);
      expect(find.byKey(const Key('tile_about_licenses')), findsOneWidget);
      expect(find.byKey(const Key('tile_about_terms')), findsOneWidget);
      expect(find.byKey(const Key('tile_about_privacy')), findsOneWidget);
      expect(find.byKey(const Key('tile_debug')), findsOneWidget);
    });

    testWidgets('shows loading indicator when settings are loading',
        (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(_NeverCompleteSettingsNotifier.new),
          ],
          child: const MaterialApp(
            home: SettingsScreen(),
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
            home: SettingsScreen(),
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
