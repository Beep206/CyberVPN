import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/diagnostics/data/services/diagnostic_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockConnectivity extends Mock implements Connectivity {}

class MockDio extends Mock implements Dio {}

class FakeOptions extends Fake implements Options {}

class FakeRequestOptions extends Fake implements RequestOptions {}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockConnectivity mockConnectivity;
  late MockDio mockDio;

  setUpAll(() {
    registerFallbackValue(FakeOptions());
    registerFallbackValue(FakeRequestOptions());
  });

  setUp(() {
    mockConnectivity = MockConnectivity();
    mockDio = MockDio();
  });

  DiagnosticService createService({
    Future<bool> Function()? vpnConnectTest,
  }) {
    return DiagnosticService(
      connectivity: mockConnectivity,
      dio: mockDio,
      vpnConnectTest: vpnConnectTest,
      baseUrl: 'https://api.example.com',
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────

  void stubConnectivityConnected() {
    when(() => mockConnectivity.checkConnectivity())
        .thenAnswer((_) async => [ConnectivityResult.wifi]);
  }

  void stubConnectivityDisconnected() {
    when(() => mockConnectivity.checkConnectivity())
        .thenAnswer((_) async => [ConnectivityResult.none]);
  }

  void stubApiHealthOk() {
    when(() => mockDio.get<dynamic>(
          any(),
          options: any(named: 'options'),
        )).thenAnswer((_) async => Response(
          requestOptions: RequestOptions(path: '/monitoring/health'),
          statusCode: 200,
        ));
  }

  void stubApiHealthError() {
    when(() => mockDio.get<dynamic>(
          any(),
          options: any(named: 'options'),
        )).thenThrow(DioException(
          requestOptions: RequestOptions(path: '/monitoring/health'),
          type: DioExceptionType.connectionTimeout,
          message: 'Connection timed out',
        ));
  }

  // ── Step 1: Network Connectivity ─────────────────────────────────────

  group('Step 1 - Network Connectivity', () {
    test('returns success when device is connected', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.networkConnectivity,
      );
      expect(step.status, DiagnosticStepStatus.success);
      expect(step.message, contains('connected'));
    });

    test('returns failure when no network connection', () async {
      stubConnectivityDisconnected();
      stubApiHealthOk();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.networkConnectivity,
      );
      expect(step.status, DiagnosticStepStatus.failed);
      expect(step.suggestion, 'Enable WiFi or mobile data');
    });

    test('returns failure on connectivity check exception', () async {
      when(() => mockConnectivity.checkConnectivity())
          .thenThrow(Exception('platform error'));
      stubApiHealthOk();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.networkConnectivity,
      );
      expect(step.status, DiagnosticStepStatus.failed);
      expect(step.suggestion, 'Enable WiFi or mobile data');
    });
  });

  // ── Step 3: API Reachability ─────────────────────────────────────────

  group('Step 3 - API Reachability', () {
    test('returns success on 200 response', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.apiReachability,
      );
      expect(step.status, DiagnosticStepStatus.success);
      expect(step.message, contains('200'));
    });

    test('returns failure on DioException', () async {
      stubConnectivityConnected();
      stubApiHealthError();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.apiReachability,
      );
      expect(step.status, DiagnosticStepStatus.failed);
      expect(step.suggestion, contains('API server may be down'));
    });

    test('returns warning on non-200 status', () async {
      stubConnectivityConnected();
      when(() => mockDio.get<dynamic>(
            any(),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response(
            requestOptions: RequestOptions(path: '/monitoring/health'),
            statusCode: 503,
          ));

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.apiReachability,
      );
      expect(step.status, DiagnosticStepStatus.warning);
      expect(step.message, contains('503'));
    });
  });

  // ── Step 4 & 5: VPN Server Handshake (no server target) ─────────────

  group('Steps 4 & 5 - Without server target', () {
    test('returns warning when no server target provided', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      final tcpStep = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.vpnTcpHandshake,
      );
      expect(tcpStep.status, DiagnosticStepStatus.warning);
      expect(tcpStep.suggestion, contains('Select a VPN server'));

      final tlsStep = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.tlsHandshake,
      );
      expect(tlsStep.status, DiagnosticStepStatus.warning);
      expect(tlsStep.suggestion, contains('Select a VPN server'));
    });
  });

  // ── Step 6: Full VPN Tunnel ──────────────────────────────────────────

  group('Step 6 - Full VPN Tunnel', () {
    test('returns success when VPN connect test succeeds', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService(
        vpnConnectTest: () async => true,
      );
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.fullTunnel,
      );
      expect(step.status, DiagnosticStepStatus.success);
      expect(step.message, contains('established'));
    });

    test('returns failure when VPN connect test returns false', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService(
        vpnConnectTest: () async => false,
      );
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.fullTunnel,
      );
      expect(step.status, DiagnosticStepStatus.failed);
      expect(step.suggestion, contains('VPN protocol error'));
    });

    test('returns failure when VPN connect test throws', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService(
        vpnConnectTest: () async => throw Exception('VPN engine crashed'),
      );
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.fullTunnel,
      );
      expect(step.status, DiagnosticStepStatus.failed);
      expect(step.suggestion, contains('VPN protocol error'));
    });

    test('returns warning when no VPN connect test callback', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService(vpnConnectTest: null);
      final steps = await service.runDiagnostics().toList();

      final step = steps.firstWhere(
        (s) => s.name == DiagnosticStepNames.fullTunnel,
      );
      expect(step.status, DiagnosticStepStatus.warning);
      expect(step.message, contains('not available'));
    });
  });

  // ── Stream emission order ────────────────────────────────────────────

  group('Stream emission', () {
    test('emits exactly 6 steps in correct order', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService();
      final steps = await service.runDiagnostics().toList();

      expect(steps, hasLength(6));
      expect(steps[0].name, DiagnosticStepNames.networkConnectivity);
      expect(steps[1].name, DiagnosticStepNames.dnsResolution);
      expect(steps[2].name, DiagnosticStepNames.apiReachability);
      expect(steps[3].name, DiagnosticStepNames.vpnTcpHandshake);
      expect(steps[4].name, DiagnosticStepNames.tlsHandshake);
      expect(steps[5].name, DiagnosticStepNames.fullTunnel);
    });
  });

  // ── runFullDiagnostics convenience method ────────────────────────────

  group('runFullDiagnostics', () {
    test('returns a DiagnosticResult with all steps', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService(vpnConnectTest: () async => true);
      final result = await service.runFullDiagnostics();

      expect(result.steps, hasLength(6));
      expect(result.ranAt, isNotNull);
      expect(result.totalDuration, isNotNull);
    });
  });

  // ── Mixed pass/fail scenarios ────────────────────────────────────────

  group('Mixed pass/fail scenarios', () {
    test('disconnected network with API error and VPN failure', () async {
      stubConnectivityDisconnected();
      stubApiHealthError();

      final service = createService(
        vpnConnectTest: () async => false,
      );
      final steps = await service.runDiagnostics().toList();

      // Network connectivity should fail
      expect(steps[0].status, DiagnosticStepStatus.failed);
      expect(steps[0].suggestion, 'Enable WiFi or mobile data');

      // DNS resolution will likely fail (no real network in test)
      // but we only assert it ran and has the right name
      expect(steps[1].name, DiagnosticStepNames.dnsResolution);

      // API reachability should fail
      expect(steps[2].status, DiagnosticStepStatus.failed);

      // VPN TCP and TLS skipped (no target)
      expect(steps[3].status, DiagnosticStepStatus.warning);
      expect(steps[4].status, DiagnosticStepStatus.warning);

      // Full tunnel should fail
      expect(steps[5].status, DiagnosticStepStatus.failed);
    });

    test('all pass scenario with mocked VPN', () async {
      stubConnectivityConnected();
      stubApiHealthOk();

      final service = createService(
        vpnConnectTest: () async => true,
      );
      // Without a server target, steps 4 and 5 will be warnings (skipped)
      final steps = await service.runDiagnostics().toList();

      expect(steps[0].status, DiagnosticStepStatus.success);
      // step 1 (DNS) will fail in test env - expected
      expect(steps[2].status, DiagnosticStepStatus.success); // API
      expect(steps[3].status, DiagnosticStepStatus.warning); // TCP - no target
      expect(steps[4].status, DiagnosticStepStatus.warning); // TLS - no target
      expect(steps[5].status, DiagnosticStepStatus.success); // VPN tunnel
    });
  });
}
