import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/logs_center_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

void main() {
  setUp(() {
    AppLogger.clearLogs();
    AppLogger.resetConfiguration();
    AppLogger.info('Buffered info message');
  });

  Widget buildScreen() {
    return ProviderScope(
      overrides: [
        settingsProvider.overrideWith(
          () => _FakeSettingsNotifier(const AppSettings(logLevel: LogLevel.info)),
        ),
        logFilesProvider.overrideWith(
          (ref) async => [
            PersistentLogFile(
              name: 'access_log.txt',
              path: '/tmp/access_log.txt',
              kind: PersistentLogFileKind.access,
              sizeBytes: 128,
              modifiedAt: DateTime(2026, 4, 17),
            ),
            PersistentLogFile(
              name: 'subscription_log.txt',
              path: '/tmp/subscription_log.txt',
              kind: PersistentLogFileKind.subscription,
              sizeBytes: 64,
              modifiedAt: DateTime(2026, 4, 17),
            ),
          ],
        ),
      ],
      child: const MaterialApp(home: LogsCenterScreen()),
    );
  }

  testWidgets('renders logs center summary and persistent files', (
    tester,
  ) async {
    await tester.pumpWidget(buildScreen());
    await tester.pumpAndSettle();

    expect(find.text('Summary'), findsOneWidget);
    expect(find.text('Diagnostics'), findsOneWidget);
    expect(find.text('Persistent Files'), findsOneWidget);
    expect(find.byKey(const Key('logs_log_level')), findsOneWidget);
    expect(find.byKey(const Key('logs_view_buffered')), findsOneWidget);
    expect(find.textContaining('1 live entry'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('logs_file_access_log.txt')),
      300,
    );
    expect(find.byKey(const Key('logs_file_access_log.txt')), findsOneWidget);
    expect(
      find.byKey(const Key('logs_file_subscription_log.txt')),
      findsOneWidget,
    );
  });
}
