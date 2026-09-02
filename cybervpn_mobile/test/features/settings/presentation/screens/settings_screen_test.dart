import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
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

Widget _buildTestWidget({AppSettings settings = const AppSettings()}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: Locale('en'),
      home: SettingsScreen(),
    ),
  );
}

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    240,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
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

      // The first five categories are visible before the lazy list scrolls.
      expect(find.byType(SettingsSection), findsNWidgets(5));
      expect(find.text('VPN Settings'), findsAtLeast(1));
      expect(find.text('Appearance'), findsAtLeast(1));
      expect(find.text('Language'), findsAtLeast(1));
      expect(find.text('Notifications'), findsAtLeast(1));
      expect(find.text('Account & Security'), findsAtLeast(1));

      await _scrollTo(tester, find.byKey(const Key('tile_about_version')));
      expect(find.text('About'), findsOneWidget);

      await _scrollTo(tester, find.byKey(const Key('tile_other_settings')));
      expect(find.text('Other Settings'), findsAtLeast(1));

      await _scrollTo(tester, find.byKey(const Key('tile_debug')));
      expect(find.text('Debug & Diagnostics'), findsOneWidget);
    });

    testWidgets('VPN Settings tile shows current protocol', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(
            preferredProtocol: PreferredProtocol.vlessReality,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('VLESS Reality'), findsOneWidget);
    });

    testWidgets('VPN Settings tile shows Auto for default protocol', (
      tester,
    ) async {
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

    testWidgets('Appearance tile shows default Cyberpunk / System', (
      tester,
    ) async {
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

    testWidgets('Language tile shows English for default locale', (
      tester,
    ) async {
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

      await _scrollTo(tester, find.byKey(const Key('tile_about_version')));

      expect(find.text('Version'), findsOneWidget);
      expect(find.text('1.0.0'), findsOneWidget);
    });

    testWidgets('About section shows legal tiles', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      await _scrollTo(tester, find.byKey(const Key('tile_about_licenses')));

      expect(find.text('Open-source licenses'), findsOneWidget);

      await _scrollTo(tester, find.byKey(const Key('tile_about_privacy')));
      expect(find.text('Privacy Policy'), findsOneWidget);
    });

    testWidgets('all navigation tiles have chevron icon', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      const navigationTileKeys = [
        'tile_vpn_settings',
        'tile_appearance',
        'tile_language',
        'tile_notifications',
        'tile_account_security',
        'tile_about_licenses',
        'tile_about_privacy',
        'tile_other_settings',
        'tile_debug',
      ];

      for (final key in navigationTileKeys) {
        final tile = find.byKey(Key(key));
        await _scrollTo(tester, tile);
        expect(
          find.descendant(of: tile, matching: find.byIcon(Icons.chevron_right)),
          findsOneWidget,
          reason: '$key should expose its navigation affordance',
        );
      }
    });

    testWidgets('all tiles have a key assigned', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      const tileKeys = [
        'tile_vpn_settings',
        'tile_appearance',
        'tile_language',
        'tile_notifications',
        'tile_account_security',
        'tile_about_version',
        'tile_about_licenses',
        'tile_about_privacy',
        'tile_other_settings',
        'tile_debug',
      ];

      for (final key in tileKeys) {
        final tile = find.byKey(Key(key));
        await _scrollTo(tester, tile);
        expect(tile, findsOneWidget);
      }
    });

    testWidgets('shows loading indicator when settings are loading', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(_NeverCompleteSettingsNotifier.new),
          ],
          child: const MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
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
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
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
  final Completer<AppSettings> _completer = Completer<AppSettings>();

  @override
  Future<AppSettings> build() => _completer.future;
}

class _ErrorSettingsNotifier extends SettingsNotifier {
  @override
  Future<AppSettings> build() async {
    throw Exception('Test error');
  }
}
