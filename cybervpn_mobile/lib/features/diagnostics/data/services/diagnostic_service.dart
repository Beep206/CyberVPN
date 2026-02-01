import 'dart:async';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';

/// Names used as the [DiagnosticStep.name] for each diagnostic check.
///
/// Exposed so consumers (providers, UI) can reference them without
/// hard-coding strings.
abstract final class DiagnosticStepNames {
  static const String networkConnectivity = 'Network Connectivity';
  static const String dnsResolution = 'DNS Resolution';
  static const String apiReachability = 'API Reachability';
  static const String vpnTcpHandshake = 'VPN Server TCP Handshake';
  static const String tlsHandshake = 'TLS/Reality Handshake';
  static const String fullTunnel = 'Full VPN Tunnel';
}

/// Configuration for a VPN server target used in TCP / TLS diagnostic steps.
class DiagnosticServerTarget {
  final String host;
  final int port;

  const DiagnosticServerTarget({required this.host, required this.port});
}

/// Service that executes a 6-step connection diagnostic sequence and
/// emits each [DiagnosticStep] result through a [Stream].
///
/// Steps executed in order:
/// 1. Network Connectivity (connectivity_plus)
/// 2. DNS Resolution (InternetAddress.lookup)
/// 3. API Reachability (HTTP GET /monitoring/health)
/// 4. VPN Server TCP Handshake (Socket.connect)
/// 5. TLS/Reality Handshake (SecureSocket.connect)
/// 6. Full VPN Tunnel (VPN engine connect/disconnect)
///
/// Each step yields a [DiagnosticStep] with pass/fail status and
/// a human-readable [DiagnosticStep.suggestion] on failure.
class DiagnosticService {
  final Connectivity _connectivity;
  final Dio _dio;

  /// Optional callback that attempts a VPN connect and returns `true` if the
  /// tunnel was successfully established. If `null` step 6 is skipped with a
  /// warning.
  final Future<bool> Function()? _vpnConnectTest;

  /// The base URL used for API-related diagnostic checks (DNS + HTTP).
  /// Defaults to [ApiConstants.baseUrl].
  final String _baseUrl;

  /// Timeout applied to individual network operations.
  static const Duration _stepTimeout = Duration(seconds: 10);

  DiagnosticService({
    Connectivity? connectivity,
    required Dio dio,
    Future<bool> Function()? vpnConnectTest,
    String? baseUrl,
  })  : _connectivity = connectivity ?? Connectivity(),
        _dio = dio,
        _vpnConnectTest = vpnConnectTest,
        _baseUrl = baseUrl ?? ApiConstants.baseUrl;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /// Runs the full 6-step diagnostic sequence and yields each step result
  /// as it completes.
  ///
  /// The returned [Stream] emits exactly 6 [DiagnosticStep] objects in order.
  /// Callers can collect them to build a [DiagnosticResult].
  Stream<DiagnosticStep> runDiagnostics({
    DiagnosticServerTarget? serverTarget,
  }) async* {
    yield await _checkNetworkConnectivity();
    yield await _checkDnsResolution();
    yield await _checkApiReachability();
    yield await _checkVpnTcpHandshake(serverTarget);
    yield await _checkTlsHandshake(serverTarget);
    yield await _checkFullTunnel();
  }

  /// Convenience method that collects all step results into a single
  /// [DiagnosticResult].
  Future<DiagnosticResult> runFullDiagnostics({
    DiagnosticServerTarget? serverTarget,
  }) async {
    final startTime = DateTime.now();
    final steps = await runDiagnostics(serverTarget: serverTarget).toList();
    final totalDuration = DateTime.now().difference(startTime);

    return DiagnosticResult(
      steps: steps,
      ranAt: startTime,
      totalDuration: totalDuration,
    );
  }

  // ---------------------------------------------------------------------------
  // Step 1: Network Connectivity
  // ---------------------------------------------------------------------------

  Future<DiagnosticStep> _checkNetworkConnectivity() async {
    final stopwatch = Stopwatch()..start();
    try {
      final results = await _connectivity
          .checkConnectivity()
          .timeout(_stepTimeout);

      stopwatch.stop();

      final connected = !results.contains(ConnectivityResult.none);
      if (connected) {
        return DiagnosticStep(
          name: DiagnosticStepNames.networkConnectivity,
          status: DiagnosticStepStatus.success,
          duration: stopwatch.elapsed,
          message: 'Device is connected to the network',
        );
      }

      return DiagnosticStep(
        name: DiagnosticStepNames.networkConnectivity,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'No network connection detected',
        suggestion: 'Enable WiFi or mobile data',
      );
    } catch (e, st) {
      stopwatch.stop();
      AppLogger.error(
        'Diagnostic: network connectivity check failed',
        error: e,
        stackTrace: st,
      );
      return DiagnosticStep(
        name: DiagnosticStepNames.networkConnectivity,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'Failed to check network connectivity: $e',
        suggestion: 'Enable WiFi or mobile data',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Step 2: DNS Resolution
  // ---------------------------------------------------------------------------

  Future<DiagnosticStep> _checkDnsResolution() async {
    final stopwatch = Stopwatch()..start();
    try {
      final host = Uri.parse(_baseUrl).host;
      final addresses = await InternetAddress.lookup(host)
          .timeout(const Duration(seconds: 5));

      stopwatch.stop();

      if (addresses.isNotEmpty) {
        return DiagnosticStep(
          name: DiagnosticStepNames.dnsResolution,
          status: DiagnosticStepStatus.success,
          duration: stopwatch.elapsed,
          message: 'Resolved $host to ${addresses.first.address}',
        );
      }

      return DiagnosticStep(
        name: DiagnosticStepNames.dnsResolution,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'DNS returned empty result for $host',
        suggestion: 'Check DNS settings or try a different network',
      );
    } catch (e, st) {
      stopwatch.stop();
      AppLogger.error(
        'Diagnostic: DNS resolution failed',
        error: e,
        stackTrace: st,
      );
      return DiagnosticStep(
        name: DiagnosticStepNames.dnsResolution,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'DNS lookup failed: $e',
        suggestion: 'Check DNS settings or try a different network',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Step 3: API Reachability
  // ---------------------------------------------------------------------------

  Future<DiagnosticStep> _checkApiReachability() async {
    final stopwatch = Stopwatch()..start();
    try {
      final response = await _dio.get<dynamic>(
        '$_baseUrl${ApiConstants.health}',
        options: Options(
          sendTimeout: _stepTimeout,
          receiveTimeout: _stepTimeout,
        ),
      );

      stopwatch.stop();

      if (response.statusCode == 200) {
        return DiagnosticStep(
          name: DiagnosticStepNames.apiReachability,
          status: DiagnosticStepStatus.success,
          duration: stopwatch.elapsed,
          message: 'API health endpoint returned 200 OK',
        );
      }

      return DiagnosticStep(
        name: DiagnosticStepNames.apiReachability,
        status: DiagnosticStepStatus.warning,
        duration: stopwatch.elapsed,
        message: 'API returned status ${response.statusCode}',
        suggestion: 'API server may be experiencing issues, try again later',
      );
    } catch (e, st) {
      stopwatch.stop();
      AppLogger.error(
        'Diagnostic: API reachability check failed',
        error: e,
        stackTrace: st,
      );
      return DiagnosticStep(
        name: DiagnosticStepNames.apiReachability,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'API unreachable: $e',
        suggestion: 'API server may be down, try again later',
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Step 4: VPN Server TCP Handshake
  // ---------------------------------------------------------------------------

  Future<DiagnosticStep> _checkVpnTcpHandshake(
    DiagnosticServerTarget? target,
  ) async {
    if (target == null) {
      return const DiagnosticStep(
        name: DiagnosticStepNames.vpnTcpHandshake,
        status: DiagnosticStepStatus.warning,
        message: 'No server target provided, skipping TCP handshake',
        suggestion: 'Select a VPN server to run full diagnostics',
      );
    }

    final stopwatch = Stopwatch()..start();
    Socket? socket;
    try {
      socket = await Socket.connect(
        target.host,
        target.port,
        timeout: _stepTimeout,
      );

      stopwatch.stop();

      return DiagnosticStep(
        name: DiagnosticStepNames.vpnTcpHandshake,
        status: DiagnosticStepStatus.success,
        duration: stopwatch.elapsed,
        message: 'TCP connection to ${target.host}:${target.port} succeeded',
      );
    } catch (e, st) {
      stopwatch.stop();
      AppLogger.error(
        'Diagnostic: VPN TCP handshake failed',
        error: e,
        stackTrace: st,
      );
      return DiagnosticStep(
        name: DiagnosticStepNames.vpnTcpHandshake,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'TCP connection to ${target.host}:${target.port} failed: $e',
        suggestion: 'VPN server unreachable, try a different server',
      );
    } finally {
      socket?.destroy();
    }
  }

  // ---------------------------------------------------------------------------
  // Step 5: TLS/Reality Handshake
  // ---------------------------------------------------------------------------

  Future<DiagnosticStep> _checkTlsHandshake(
    DiagnosticServerTarget? target,
  ) async {
    if (target == null) {
      return const DiagnosticStep(
        name: DiagnosticStepNames.tlsHandshake,
        status: DiagnosticStepStatus.warning,
        message: 'No server target provided, skipping TLS handshake',
        suggestion: 'Select a VPN server to run full diagnostics',
      );
    }

    final stopwatch = Stopwatch()..start();
    SecureSocket? secureSocket;
    try {
      secureSocket = await SecureSocket.connect(
        target.host,
        target.port,
        timeout: _stepTimeout,
        onBadCertificate: (_) => true, // Accept self-signed for diagnostic
      );

      stopwatch.stop();

      return DiagnosticStep(
        name: DiagnosticStepNames.tlsHandshake,
        status: DiagnosticStepStatus.success,
        duration: stopwatch.elapsed,
        message: 'TLS handshake with ${target.host}:${target.port} succeeded',
      );
    } catch (e, st) {
      stopwatch.stop();
      AppLogger.error(
        'Diagnostic: TLS handshake failed',
        error: e,
        stackTrace: st,
      );
      return DiagnosticStep(
        name: DiagnosticStepNames.tlsHandshake,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'TLS handshake failed: $e',
        suggestion: 'TLS configuration error, contact support',
      );
    } finally {
      secureSocket?.destroy();
    }
  }

  // ---------------------------------------------------------------------------
  // Step 6: Full VPN Tunnel
  // ---------------------------------------------------------------------------

  Future<DiagnosticStep> _checkFullTunnel() async {
    if (_vpnConnectTest == null) {
      return const DiagnosticStep(
        name: DiagnosticStepNames.fullTunnel,
        status: DiagnosticStepStatus.warning,
        message: 'VPN connect test not available',
        suggestion: 'VPN engine not configured for diagnostics',
      );
    }

    final stopwatch = Stopwatch()..start();
    try {
      final success = await _vpnConnectTest().timeout(_stepTimeout);

      stopwatch.stop();

      if (success) {
        return DiagnosticStep(
          name: DiagnosticStepNames.fullTunnel,
          status: DiagnosticStepStatus.success,
          duration: stopwatch.elapsed,
          message: 'VPN tunnel established successfully',
        );
      }

      return DiagnosticStep(
        name: DiagnosticStepNames.fullTunnel,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'VPN tunnel could not be established',
        suggestion: 'VPN protocol error, check server settings',
      );
    } catch (e, st) {
      stopwatch.stop();
      AppLogger.error(
        'Diagnostic: full tunnel test failed',
        error: e,
        stackTrace: st,
      );
      return DiagnosticStep(
        name: DiagnosticStepNames.fullTunnel,
        status: DiagnosticStepStatus.failed,
        duration: stopwatch.elapsed,
        message: 'VPN tunnel test failed: $e',
        suggestion: 'VPN protocol error, check server settings',
      );
    }
  }
}
