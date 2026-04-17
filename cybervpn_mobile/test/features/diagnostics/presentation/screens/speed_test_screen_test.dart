import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lottie/lottie.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/providers/diagnostics_provider.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/speed_test_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/speedometer_gauge.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/speed_test_results_card.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testResult = SpeedTestResult(
  downloadMbps: 85.3,
  uploadMbps: 42.1,
  latencyMs: 12,
  jitterMs: 3,
  testedAt: DateTime(2026, 1, 31, 14, 30),
  vpnActive: true,
  serverName: 'US East 1',
);

final _olderResult = SpeedTestResult(
  downloadMbps: 72.0,
  uploadMbps: 38.5,
  latencyMs: 18,
  jitterMs: 5,
  testedAt: DateTime(2026, 1, 31, 13, 0),
  vpnActive: true,
  serverName: 'US East 1',
);

// ---------------------------------------------------------------------------
// Fake DiagnosticsNotifier
// ---------------------------------------------------------------------------

class _FakeDiagnosticsNotifier extends AsyncNotifier<DiagnosticsState>
    implements DiagnosticsNotifier {
  _FakeDiagnosticsNotifier(this._state);

  final DiagnosticsState _state;
  bool runSpeedTestCalled = false;
  PingMode? lastPingMode;
  String? lastPingTestUrl;

  @override
  Future<DiagnosticsState> build() async => _state;

  @override
  Future<void> runSpeedTest({
    bool vpnActive = false,
    String? serverName,
    PingMode pingMode = PingMode.tcp,
    String? pingTestUrl,
  }) async {
    runSpeedTestCalled = true;
    lastPingMode = pingMode;
    lastPingTestUrl = pingTestUrl;
  }

  @override
  Future<void> runDiagnostics({dynamic serverTarget}) async {}

  @override
  List<SpeedTestResult> getHistory() => _state.speedHistory;

  @override
  String exportLogs() => '[]';
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

void _ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final exception = details.exception;
    final isOverflow =
        exception is FlutterError && exception.message.contains('overflowed');
    if (!isOverflow) {
      FlutterError.presentError(details);
    }
  };
}

Widget _buildTestWidget({
  required DiagnosticsState state,
  _FakeDiagnosticsNotifier? notifier,
  AppSettings settings = const AppSettings(),
}) {
  final fakeNotifier = notifier ?? _FakeDiagnosticsNotifier(state);

  final fakeSettingsNotifier = _FakeSettingsNotifier(settings);

  return ProviderScope(
    overrides: [
      // Override the async notifier itself
      diagnosticsProvider.overrideWith(() => fakeNotifier),
      settingsProvider.overrideWith(() => fakeSettingsNotifier),
      // Override all derived providers so they don't depend on the async resolution
      speedTestProgressProvider.overrideWithValue(state.isRunningSpeedTest),
      latestSpeedTestProvider.overrideWithValue(state.speedTestResult),
      speedHistoryProvider.overrideWithValue(state.speedHistory),
    ],
    child: const MaterialApp(
      locale: Locale('en'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      home: SpeedTestScreen(),
    ),
  );
}

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier(this._settings);

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(_ignoreOverflowErrors);

  // Use a phone-sized surface to fit the gauge + button + content.
  const testSurfaceSize = Size(430, 932);

  group('SpeedTestScreen', () {
    testWidgets('renders gauge and start button in idle state', (tester) async {
      tester.view.physicalSize = testSurfaceSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        _buildTestWidget(state: const DiagnosticsState()),
      );
      await tester.pumpAndSettle();

      expect(find.byType(SpeedometerGauge), findsOneWidget);
      expect(find.text('Start Speed Test'), findsOneWidget);
      expect(find.text('No speed tests yet'), findsOneWidget);
      expect(find.byKey(const Key('speed_test_ping_summary')), findsOneWidget);
    });

    testWidgets('shows running indicator when test is in progress', (
      tester,
    ) async {
      tester.view.physicalSize = testSurfaceSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        _buildTestWidget(
          state: const DiagnosticsState(isRunningSpeedTest: true),
        ),
      );
      // Use pump() instead of pumpAndSettle() because
      // CircularProgressIndicator animates indefinitely.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Testing...'), findsOneWidget);
      expect(find.byType(LottieBuilder), findsOneWidget);
    });

    testWidgets('displays results card after test completion', (tester) async {
      tester.view.physicalSize = testSurfaceSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        _buildTestWidget(
          state: DiagnosticsState(
            speedTestResult: _testResult,
            speedHistory: [_testResult],
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(SpeedTestResultsCard), findsOneWidget);
      expect(find.text('85.3'), findsWidgets);
      expect(find.text('42.1'), findsWidgets);
    });

    testWidgets('renders history list with entries', (tester) async {
      tester.view.physicalSize = testSurfaceSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      await tester.pumpWidget(
        _buildTestWidget(
          state: DiagnosticsState(
            speedTestResult: _testResult,
            speedHistory: [_testResult, _olderResult],
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('History'), findsOneWidget);
      // Results card values + history tile values (some may be offscreen)
      expect(find.text('85.3', skipOffstage: false), findsWidgets);
      expect(find.text('72.0', skipOffstage: false), findsWidgets);
    });

    testWidgets('tapping start button triggers speed test', (tester) async {
      tester.view.physicalSize = testSurfaceSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final notifier = _FakeDiagnosticsNotifier(const DiagnosticsState());

      await tester.pumpWidget(
        _buildTestWidget(state: const DiagnosticsState(), notifier: notifier),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Start Speed Test'));
      await tester.pump();

      expect(notifier.runSpeedTestCalled, isTrue);
      expect(notifier.lastPingMode, PingMode.tcp);
      expect(notifier.lastPingTestUrl, 'https://google.com/generate_204');
    });

    testWidgets('uses current ping preferences from settings', (tester) async {
      tester.view.physicalSize = testSurfaceSize;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final notifier = _FakeDiagnosticsNotifier(const DiagnosticsState());

      await tester.pumpWidget(
        _buildTestWidget(
          state: const DiagnosticsState(),
          notifier: notifier,
          settings: const AppSettings(
            pingMode: PingMode.realDelay,
            pingTestUrl: 'https://example.com/generate_204',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Latency mode: Via Proxy HEAD'),
        findsOneWidget,
      );

      await tester.tap(find.text('Start Speed Test'));
      await tester.pump();

      expect(notifier.lastPingMode, PingMode.realDelay);
      expect(notifier.lastPingTestUrl, 'https://example.com/generate_204');
    });
  });

  group('SpeedometerGauge', () {
    testWidgets('renders without error at various speeds', (tester) async {
      for (final speed in [0.0, 25.0, 50.0, 75.0, 100.0]) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Center(child: SpeedometerGauge(speed: speed, size: 200)),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byType(SpeedometerGauge), findsOneWidget);
        expect(find.byType(CustomPaint), findsWidgets);
      }
    });

    testWidgets('displays speed value text in center', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(child: SpeedometerGauge(speed: 50.0, size: 200)),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('50.0'), findsOneWidget);
      expect(find.text('Mbps'), findsOneWidget);
    });

    testWidgets('animates needle when speed changes', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SpeedometerGauge(
                speed: 0.0,
                size: 200,
                animationDuration: Duration(milliseconds: 300),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SpeedometerGauge(
                speed: 80.0,
                size: 200,
                animationDuration: Duration(milliseconds: 300),
              ),
            ),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 150));
      expect(find.byType(SpeedometerGauge), findsOneWidget);

      await tester.pumpAndSettle();
      expect(find.text('80.0'), findsOneWidget);
    });
  });

  group('SpeedTestResultsCard', () {
    testWidgets('displays all metric values', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          locale: const Locale('en'),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          home: Scaffold(
            body: SingleChildScrollView(
              child: SpeedTestResultsCard(result: _testResult),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Speed Test Result'), findsOneWidget);
      expect(find.text('85.3'), findsOneWidget);
      expect(find.text('42.1'), findsOneWidget);
      expect(find.text('12'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('VPN ON'), findsOneWidget);
    });

    testWidgets('shows compare button when previous result exists', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          locale: const Locale('en'),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          home: Scaffold(
            body: SingleChildScrollView(
              child: SpeedTestResultsCard(
                result: _testResult,
                previousResult: _olderResult,
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Compare'), findsOneWidget);
      expect(find.text('Share'), findsOneWidget);
    });
  });
}
