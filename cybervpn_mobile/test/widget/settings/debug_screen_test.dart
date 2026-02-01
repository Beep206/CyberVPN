import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/debug_screen.dart';
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

  @override
  Future<void> updateLogLevel(LogLevel level) async {
    // No-op for tests
  }

  @override
  Future<void> resetAll() async {
    // No-op for tests
  }
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
      home: DebugScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('DebugScreen', () {
    testWidgets('renders Debug & About title in AppBar', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Debug & About'), findsOneWidget);
    });

    testWidgets('renders all settings sections', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // There should be 3 SettingsSection widgets:
      // Diagnostics, Cache & Data, About
      expect(find.byType(SettingsSection), findsNWidgets(3));

      // Verify section titles.
      expect(find.text('Diagnostics'), findsOneWidget);
      expect(find.text('Cache & Data'), findsOneWidget);
      expect(find.text('About'), findsOneWidget);
    });

    testWidgets('Log Level tile shows current level', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(logLevel: LogLevel.debug),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Log Level'), findsOneWidget);
      expect(find.text('Debug'), findsOneWidget);
    });

    testWidgets('Log Level tile shows Info for default level', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Log Level'), findsOneWidget);
      expect(find.text('Info'), findsOneWidget);
    });

    testWidgets('Export Logs tile shows entry count', (tester) async {
      // Clear logs first
      AppLogger.clearLogs();

      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Export Logs'), findsOneWidget);
      expect(find.text('0 entries'), findsOneWidget);
    });

    testWidgets('tapping Log Level tile shows dialog', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Tap the Log Level tile
      await tester.tap(find.byKey(const Key('tile_log_level')));
      await tester.pumpAndSettle();

      // Dialog should appear
      expect(find.text('Log Level'), findsNWidgets(2)); // Title + tile
      expect(find.text('Debug'), findsAtLeast(1));
      expect(find.text('Info'), findsAtLeast(1));
      expect(find.text('Warning'), findsAtLeast(1));
      expect(find.text('Error'), findsAtLeast(1));
    });

    testWidgets('tapping Export Logs shows share functionality', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Tap the Export Logs tile
      await tester.tap(find.byKey(const Key('tile_export_logs')));
      await tester.pumpAndSettle();

      // Should show snackbar when no logs exist
      expect(find.text('No logs to export'), findsOneWidget);
    });

    testWidgets('tapping Clear Cache shows confirmation dialog', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Tap the Clear Cache tile
      await tester.tap(find.byKey(const Key('tile_clear_cache')));
      await tester.pumpAndSettle();

      // Confirmation dialog should appear
      expect(find.text('Clear Cache?'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Clear'), findsOneWidget);
    });

    testWidgets('tapping Reset Settings shows confirmation dialog', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Tap the Reset Settings tile
      await tester.tap(find.byKey(const Key('tile_reset_settings')));
      await tester.pumpAndSettle();

      // Confirmation dialog should appear
      expect(find.text('Reset All Settings?'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Reset'), findsOneWidget);
    });

    testWidgets('tapping version 7 times activates developer mode', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Developer panel should not be visible initially
      expect(find.text('Developer Options'), findsNothing);

      // Tap version tile 7 times
      for (var i = 0; i < 7; i++) {
        await tester.tap(find.byKey(const Key('tile_app_version')));
        await tester.pump(const Duration(milliseconds: 100));
      }
      await tester.pumpAndSettle();

      // Developer panel should now be visible
      expect(find.text('Developer Options'), findsOneWidget);
      expect(find.text('Raw VPN Config Viewer'), findsOneWidget);
      expect(find.text('Force Crash (Sentry Test)'), findsOneWidget);
      expect(find.text('Experimental Features'), findsOneWidget);

      // Snackbar should show activation message
      expect(find.text('Developer mode activated'), findsOneWidget);
    });

    testWidgets('developer mode shows all developer tiles', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Activate developer mode
      for (var i = 0; i < 7; i++) {
        await tester.tap(find.byKey(const Key('tile_app_version')));
        await tester.pump(const Duration(milliseconds: 100));
      }
      await tester.pumpAndSettle();

      // Verify all developer tiles are present
      expect(find.byKey(const Key('tile_developer_raw_config')), findsOneWidget);
      expect(find.byKey(const Key('tile_developer_force_crash')), findsOneWidget);
      expect(find.byKey(const Key('tile_developer_experimental')), findsOneWidget);
    });

    testWidgets('all tiles have keys assigned', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('tile_log_level')), findsOneWidget);
      expect(find.byKey(const Key('tile_export_logs')), findsOneWidget);
      expect(find.byKey(const Key('tile_clear_cache')), findsOneWidget);
      expect(find.byKey(const Key('tile_reset_settings')), findsOneWidget);
      expect(find.byKey(const Key('tile_app_version')), findsOneWidget);
      expect(find.byKey(const Key('tile_xray_version')), findsOneWidget);
    });

    testWidgets('shows loading indicator when settings are loading', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(_NeverCompleteSettingsNotifier.new),
          ],
          child: const MaterialApp(
            home: DebugScreen(),
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
            home: DebugScreen(),
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
