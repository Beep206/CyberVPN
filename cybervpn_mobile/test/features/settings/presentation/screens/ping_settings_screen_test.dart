import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/ping_settings_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> updatePingSettings({
    required PingMode mode,
    String? pingTestUrl,
  }) async {
    _settings = _settings.copyWith(
      pingMode: mode,
      pingTestUrl: pingTestUrl ?? _settings.pingTestUrl,
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> updatePingDisplayMode(PingDisplayMode displayMode) async {
    _settings = _settings.copyWith(pingDisplayMode: displayMode);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updatePingResultMode(PingResultMode resultMode) async {
    _settings = _settings.copyWith(
      pingResultMode: resultMode,
      pingDisplayMode: switch (resultMode) {
        PingResultMode.time => PingDisplayMode.latency,
        PingResultMode.icon => PingDisplayMode.quality,
      },
    );
    state = AsyncData(_settings);
  }
}

Widget _buildTestWidget({required _FakeSettingsNotifier notifier}) {
  return ProviderScope(
    overrides: [settingsProvider.overrideWith(() => notifier)],
    child: const MaterialApp(home: PingSettingsScreen()),
  );
}

void main() {
  group('PingSettingsScreen', () {
    testWidgets('renders ping mode, result, and diagnostics controls', (
      tester,
    ) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('radio_ping_mode_tcp')), findsOneWidget);
      expect(find.byKey(const Key('radio_ping_mode_proxy_get')), findsOneWidget);
      expect(
        find.byKey(const Key('radio_ping_mode_proxy_head')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('radio_ping_mode_icmp')), findsOneWidget);
      expect(find.byKey(const Key('radio_ping_result_time')), findsOneWidget);
      expect(find.byKey(const Key('radio_ping_result_icon')), findsOneWidget);
      expect(find.byKey(const Key('input_ping_test_url')), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byKey(const Key('info_ping_runtime_fallbacks')),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('info_ping_runtime_fallbacks')), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byKey(const Key('nav_ping_speed_test')),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('nav_ping_speed_test')), findsOneWidget);
    });

    testWidgets('updates ping mode, result mode, and target url', (
      tester,
    ) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('radio_ping_mode_proxy_head')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('radio_ping_result_icon')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('input_ping_test_url')),
        'https://example.com/generate_204',
      );
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      expect(notifier._settings.pingMode, PingMode.proxyHead);
      expect(notifier._settings.pingResultMode, PingResultMode.icon);
      expect(notifier._settings.pingDisplayMode, PingDisplayMode.quality);
      expect(
        notifier._settings.pingTestUrl,
        'https://example.com/generate_204',
      );
    });
  });
}
