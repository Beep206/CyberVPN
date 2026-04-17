import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/ping_policy_runtime.dart';

void main() {
  const runtime = PingPolicyRuntime();

  group('PingPolicyRuntime', () {
    test('normalizes legacy realDelay to proxyHead', () {
      expect(runtime.normalizeMode(PingMode.realDelay), PingMode.proxyHead);
    });

    test('maps icon/time result modes to legacy display modes', () {
      expect(
        runtime.displayModeForResult(PingResultMode.icon),
        PingDisplayMode.quality,
      );
      expect(
        runtime.resultModeForDisplay(PingDisplayMode.latency),
        PingResultMode.time,
      );
    });

    test('uses proxy transport for diagnostics proxy modes', () {
      final plan = runtime.resolveDiagnosticsPlan(PingMode.proxyGet);

      expect(plan.effectiveTransport, PingTransport.proxyGet);
      expect(plan.isFallback, isFalse);
    });

    test('falls back to TCP for server-list proxy modes', () {
      final plan = runtime.resolveServerListPlan(PingMode.proxyHead);

      expect(plan.effectiveTransport, PingTransport.tcp);
      expect(plan.isFallback, isTrue);
      expect(plan.fallbackReason, contains('Server-list ping'));
    });

    test('falls back to TCP for ICMP everywhere', () {
      final plan = runtime.resolveDiagnosticsPlan(PingMode.icmp);

      expect(plan.effectiveTransport, PingTransport.tcp);
      expect(plan.isFallback, isTrue);
      expect(plan.fallbackReason, contains('ICMP'));
    });

    test('profile plan uses proxy transport when config data exists', () {
      final plan = runtime.resolveProfilePlan(
        PingMode.proxyHead,
        hasConfigData: true,
      );

      expect(plan.effectiveTransport, PingTransport.proxyHead);
      expect(plan.isFallback, isFalse);
    });

    test('profile plan falls back when config data is missing', () {
      final plan = runtime.resolveProfilePlan(
        PingMode.proxyGet,
        hasConfigData: false,
      );

      expect(plan.effectiveTransport, PingTransport.tcp);
      expect(plan.isFallback, isTrue);
      expect(plan.fallbackReason, contains('does not have a full runtime config'));
    });
  });
}
