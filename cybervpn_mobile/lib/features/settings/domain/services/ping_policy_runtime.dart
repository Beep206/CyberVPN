import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';

enum PingTransport { tcp, proxyGet, proxyHead }

class PingExecutionPlan {
  const PingExecutionPlan({
    required this.requestedMode,
    required this.effectiveTransport,
    this.fallbackReason,
  });

  final PingMode requestedMode;
  final PingTransport effectiveTransport;
  final String? fallbackReason;

  bool get isFallback =>
      fallbackReason != null && fallbackReason!.trim().isNotEmpty;

  bool get usesProxyRequest => effectiveTransport != PingTransport.tcp;
}

/// Normalizes Happ-like ping preferences into executable runtime plans.
class PingPolicyRuntime {
  const PingPolicyRuntime();

  PingMode normalizeMode(PingMode mode) {
    return switch (mode) {
      PingMode.realDelay => PingMode.proxyHead,
      _ => mode,
    };
  }

  PingExecutionPlan resolveDiagnosticsPlan(PingMode mode) {
    final normalized = normalizeMode(mode);
    return switch (normalized) {
      PingMode.tcp => const PingExecutionPlan(
          requestedMode: PingMode.tcp,
          effectiveTransport: PingTransport.tcp,
        ),
      PingMode.proxyGet => const PingExecutionPlan(
          requestedMode: PingMode.proxyGet,
          effectiveTransport: PingTransport.proxyGet,
        ),
      PingMode.proxyHead => const PingExecutionPlan(
          requestedMode: PingMode.proxyHead,
          effectiveTransport: PingTransport.proxyHead,
        ),
      PingMode.icmp => const PingExecutionPlan(
          requestedMode: PingMode.icmp,
          effectiveTransport: PingTransport.tcp,
          fallbackReason:
              'ICMP ping is unavailable on the current mobile runtime; falling back to TCP connect.',
        ),
      PingMode.realDelay => throw StateError('normalizeMode must run first'),
    };
  }

  PingExecutionPlan resolveServerListPlan(PingMode mode) {
    final normalized = normalizeMode(mode);
    return switch (normalized) {
      PingMode.tcp => const PingExecutionPlan(
          requestedMode: PingMode.tcp,
          effectiveTransport: PingTransport.tcp,
        ),
      PingMode.proxyGet => const PingExecutionPlan(
          requestedMode: PingMode.proxyGet,
          effectiveTransport: PingTransport.tcp,
          fallbackReason:
              'Server-list ping uses panel host/port metadata only, so proxy GET falls back to TCP connect.',
        ),
      PingMode.proxyHead => const PingExecutionPlan(
          requestedMode: PingMode.proxyHead,
          effectiveTransport: PingTransport.tcp,
          fallbackReason:
              'Server-list ping uses panel host/port metadata only, so proxy HEAD falls back to TCP connect.',
        ),
      PingMode.icmp => const PingExecutionPlan(
          requestedMode: PingMode.icmp,
          effectiveTransport: PingTransport.tcp,
          fallbackReason:
              'ICMP ping is unavailable on the current mobile runtime; falling back to TCP connect.',
        ),
      PingMode.realDelay => throw StateError('normalizeMode must run first'),
    };
  }

  PingExecutionPlan resolveProfilePlan(
    PingMode mode, {
    required bool hasConfigData,
  }) {
    final normalized = normalizeMode(mode);

    if (!hasConfigData) {
      return switch (normalized) {
        PingMode.tcp => const PingExecutionPlan(
            requestedMode: PingMode.tcp,
            effectiveTransport: PingTransport.tcp,
          ),
        PingMode.proxyGet => const PingExecutionPlan(
            requestedMode: PingMode.proxyGet,
            effectiveTransport: PingTransport.tcp,
            fallbackReason:
                'Subscription ping does not have a full runtime config for this server, so proxy GET falls back to TCP connect.',
          ),
        PingMode.proxyHead => const PingExecutionPlan(
            requestedMode: PingMode.proxyHead,
            effectiveTransport: PingTransport.tcp,
            fallbackReason:
                'Subscription ping does not have a full runtime config for this server, so proxy HEAD falls back to TCP connect.',
          ),
        PingMode.icmp => const PingExecutionPlan(
            requestedMode: PingMode.icmp,
            effectiveTransport: PingTransport.tcp,
            fallbackReason:
                'ICMP ping is unavailable on the current mobile runtime; falling back to TCP connect.',
          ),
        PingMode.realDelay => throw StateError('normalizeMode must run first'),
      };
    }

    return switch (normalized) {
      PingMode.tcp => const PingExecutionPlan(
          requestedMode: PingMode.tcp,
          effectiveTransport: PingTransport.tcp,
        ),
      PingMode.proxyGet => const PingExecutionPlan(
          requestedMode: PingMode.proxyGet,
          effectiveTransport: PingTransport.proxyGet,
        ),
      PingMode.proxyHead => const PingExecutionPlan(
          requestedMode: PingMode.proxyHead,
          effectiveTransport: PingTransport.proxyHead,
        ),
      PingMode.icmp => const PingExecutionPlan(
          requestedMode: PingMode.icmp,
          effectiveTransport: PingTransport.tcp,
          fallbackReason:
              'ICMP ping is unavailable on the current mobile runtime; falling back to TCP connect.',
        ),
      PingMode.realDelay => throw StateError('normalizeMode must run first'),
    };
  }

  PingDisplayMode displayModeForResult(PingResultMode mode) {
    return switch (mode) {
      PingResultMode.time => PingDisplayMode.latency,
      PingResultMode.icon => PingDisplayMode.quality,
    };
  }

  PingResultMode resultModeForDisplay(PingDisplayMode mode) {
    return switch (mode) {
      PingDisplayMode.latency => PingResultMode.time,
      PingDisplayMode.quality => PingResultMode.icon,
    };
  }

  String modeLabel(PingMode mode) {
    final normalized = normalizeMode(mode);
    return switch (normalized) {
      PingMode.tcp => 'TCP',
      PingMode.proxyGet => 'Via Proxy GET',
      PingMode.proxyHead => 'Via Proxy HEAD',
      PingMode.icmp => 'ICMP',
      PingMode.realDelay => 'Via Proxy HEAD',
    };
  }
}
