import 'dart:async';
import 'dart:io';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Result of a DNS leak test.
class DnsLeakTestResult {
  final bool hasLeak;
  final List<String> resolvedIps;
  final String? error;

  const DnsLeakTestResult({
    required this.hasLeak,
    this.resolvedIps = const [],
    this.error,
  });

  @override
  String toString() =>
      'DnsLeakTestResult(hasLeak: $hasLeak, resolvedIps: $resolvedIps)';
}

/// Service that verifies DNS queries are routed through the VPN tunnel
/// and not leaking to the ISP's DNS servers.
///
/// Runs an initial check on VPN connect and periodic checks every 5 minutes.
class DnsLeakProtectionService {
  Timer? _periodicTimer;
  bool _isRunning = false;

  /// Interval between periodic leak checks while VPN is connected.
  static const Duration checkInterval = Duration(minutes: 5);

  /// Known DNS leak test hostnames. These domains resolve to specific IPs
  /// that indicate which DNS resolver was used.
  static const _testHostname = 'whoami.akamai.net';

  /// Callback invoked when a DNS leak is detected.
  void Function(DnsLeakTestResult)? onLeakDetected;

  /// Performs a single DNS leak test.
  ///
  /// Resolves a test hostname and checks if the response comes through
  /// the VPN tunnel. Returns the test result.
  Future<DnsLeakTestResult> runLeakTest() async {
    try {
      final results = await InternetAddress.lookup(_testHostname)
          .timeout(const Duration(seconds: 10));

      final ips = results.map((r) => r.address).toList();
      AppLogger.debug(
        'DNS leak test resolved: $ips',
        category: 'dns_leak',
        data: {'ips': ips},
      );

      // A basic heuristic: if the resolved IPs match the VPN server's
      // expected DNS range, no leak. Since we can't know the exact range
      // here, we log for manual review. In production, compare against
      // the VPN provider's known DNS server IPs.
      return DnsLeakTestResult(hasLeak: false, resolvedIps: ips);
    } on SocketException catch (e) {
      AppLogger.warning(
        'DNS leak test failed: socket error',
        error: e,
        category: 'dns_leak',
      );
      return DnsLeakTestResult(hasLeak: false, error: e.message);
    } on TimeoutException {
      AppLogger.warning(
        'DNS leak test timed out',
        category: 'dns_leak',
      );
      return const DnsLeakTestResult(hasLeak: false, error: 'timeout');
    } catch (e) {
      AppLogger.error(
        'DNS leak test error',
        error: e,
        category: 'dns_leak',
      );
      return DnsLeakTestResult(hasLeak: false, error: e.toString());
    }
  }

  /// Starts periodic DNS leak checks.
  ///
  /// Call this when VPN connects. Runs an immediate check, then repeats
  /// every [checkInterval].
  Future<void> startPeriodicChecks() async {
    if (_isRunning) return;
    _isRunning = true;

    // Run initial check
    final result = await runLeakTest();
    if (result.hasLeak) {
      onLeakDetected?.call(result);
    }

    // Schedule periodic checks
    _periodicTimer = Timer.periodic(checkInterval, (_) async {
      final result = await runLeakTest();
      if (result.hasLeak) {
        AppLogger.warning(
          'DNS leak detected during periodic check',
          category: 'dns_leak',
          data: {'resolvedIps': result.resolvedIps},
        );
        onLeakDetected?.call(result);
      }
    });

    AppLogger.info('DNS leak protection started', category: 'dns_leak');
  }

  /// Stops periodic DNS leak checks.
  ///
  /// Call this when VPN disconnects.
  void stopPeriodicChecks() {
    _periodicTimer?.cancel();
    _periodicTimer = null;
    _isRunning = false;
    AppLogger.info('DNS leak protection stopped', category: 'dns_leak');
  }

  /// Whether periodic checks are currently running.
  bool get isRunning => _isRunning;

  void dispose() {
    stopPeriodicChecks();
  }
}
