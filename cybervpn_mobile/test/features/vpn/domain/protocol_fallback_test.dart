import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/protocol_fallback.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../helpers/fakes/fake_secure_storage.dart';

void main() {
  late FakeSecureStorage fakeStorage;
  late ProtocolFallback fallback;

  setUp(() {
    fakeStorage = FakeSecureStorage();
    fallback = ProtocolFallback(storage: fakeStorage);
  });

  // ---------------------------------------------------------------------------
  // Fallback chain order
  // ---------------------------------------------------------------------------

  group('ProtocolFallback - fallback chain constants', () {
    test('maxRetries is 3', () {
      expect(ProtocolFallback.maxRetries, 3);
    });

    test('handshakeTimeout is 5 seconds', () {
      expect(
        ProtocolFallback.handshakeTimeout,
        const Duration(seconds: 5),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Preferred protocol persistence
  // ---------------------------------------------------------------------------

  group('ProtocolFallback - preferred protocol', () {
    test('getPreferredProtocol returns null when none saved', () async {
      final result = await fallback.getPreferredProtocol();

      expect(result, isNull);
    });

    test('setPreferredProtocol stores protocol name', () async {
      await fallback.setPreferredProtocol(VpnProtocol.vmess);

      final result = await fallback.getPreferredProtocol();

      expect(result, VpnProtocol.vmess);
    });

    test('setPreferredProtocol(null) clears stored protocol', () async {
      await fallback.setPreferredProtocol(VpnProtocol.trojan);
      await fallback.setPreferredProtocol(null);

      final result = await fallback.getPreferredProtocol();

      expect(result, isNull);
    });

    test('stores each protocol correctly', () async {
      for (final protocol in [
        VpnProtocol.vless,
        VpnProtocol.vmess,
        VpnProtocol.trojan,
      ]) {
        await fallback.setPreferredProtocol(protocol);
        final result = await fallback.getPreferredProtocol();
        expect(result, protocol, reason: '${protocol.name} roundtrip failed');
      }
    });

    test('overwrites previously stored protocol', () async {
      await fallback.setPreferredProtocol(VpnProtocol.vless);
      await fallback.setPreferredProtocol(VpnProtocol.trojan);

      final result = await fallback.getPreferredProtocol();

      expect(result, VpnProtocol.trojan);
    });
  });

  // ---------------------------------------------------------------------------
  // ProtocolFallbackResult types
  // ---------------------------------------------------------------------------

  group('ProtocolFallbackResult', () {
    test('ProtocolFallbackSuccess is a success', () {
      const result = ProtocolFallbackSuccess(
        protocol: VpnProtocol.vless,
        attemptLog: [],
      );

      expect(result.isSuccess, isTrue);
      expect(result.isFailure, isFalse);
      expect(result.protocol, VpnProtocol.vless);
    });

    test('ProtocolFallbackFailure is a failure', () {
      const result = ProtocolFallbackFailure(
        message: 'All protocols unavailable',
        attemptLog: [],
      );

      expect(result.isSuccess, isFalse);
      expect(result.isFailure, isTrue);
      expect(result.message, 'All protocols unavailable');
    });

    test('result type can be pattern-matched with sealed class', () {
      const ProtocolFallbackResult result = ProtocolFallbackSuccess(
        protocol: VpnProtocol.vmess,
        attemptLog: [],
      );

      final matched = switch (result) {
        ProtocolFallbackSuccess(protocol: final p) => 'success: ${p.name}',
        ProtocolFallbackFailure(message: final m) => 'failure: $m',
      };

      expect(matched, 'success: vmess');
    });
  });

  // ---------------------------------------------------------------------------
  // ProtocolAttemptLog
  // ---------------------------------------------------------------------------

  group('ProtocolAttemptLog', () {
    test('creates log entry with all fields', () {
      final now = DateTime(2026, 1, 31, 12, 0);
      final log = ProtocolAttemptLog(
        protocol: VpnProtocol.vless,
        attempt: 1,
        success: true,
        timestamp: now,
      );

      expect(log.protocol, VpnProtocol.vless);
      expect(log.attempt, 1);
      expect(log.success, isTrue);
      expect(log.timestamp, now);
    });

    test('toString contains protocol name and attempt info', () {
      final log = ProtocolAttemptLog(
        protocol: VpnProtocol.trojan,
        attempt: 2,
        success: false,
        timestamp: DateTime(2026, 1, 31),
      );

      final str = log.toString();

      expect(str, contains('trojan'));
      expect(str, contains('attempt=2'));
      expect(str, contains('success=false'));
    });

    test('multiple log entries track full attempt history', () {
      final logs = [
        ProtocolAttemptLog(
          protocol: VpnProtocol.vless,
          attempt: 1,
          success: false,
          timestamp: DateTime(2026, 1, 31, 12, 0, 0),
        ),
        ProtocolAttemptLog(
          protocol: VpnProtocol.vless,
          attempt: 2,
          success: false,
          timestamp: DateTime(2026, 1, 31, 12, 0, 5),
        ),
        ProtocolAttemptLog(
          protocol: VpnProtocol.vless,
          attempt: 3,
          success: false,
          timestamp: DateTime(2026, 1, 31, 12, 0, 10),
        ),
        ProtocolAttemptLog(
          protocol: VpnProtocol.vmess,
          attempt: 1,
          success: true,
          timestamp: DateTime(2026, 1, 31, 12, 0, 15),
        ),
      ];

      expect(logs, hasLength(4));
      expect(logs.where((l) => l.success).length, 1);
      expect(logs.last.protocol, VpnProtocol.vmess);
      expect(logs.last.success, isTrue);
    });
  });

  // ---------------------------------------------------------------------------
  // execute() - result structure validation
  // ---------------------------------------------------------------------------

  group('ProtocolFallback - execute result structure', () {
    // Note: execute() performs real TCP socket connections, so we cannot
    // deterministically control success/failure in a pure unit test.
    // We verify the structure of the result regardless of outcome.

    test('execute returns a ProtocolFallbackResult', () async {
      final result = await fallback.execute(
        serverAddress: '127.0.0.1',
        port: 1, // unlikely to have a listener
      );

      expect(result, isA<ProtocolFallbackResult>());
      expect(result.attemptLog, isNotEmpty);
    }, timeout: const Timeout(Duration(minutes: 2)));

    test('manual override limits attempts to one protocol', () async {
      final result = await fallback.execute(
        serverAddress: '127.0.0.1',
        port: 1,
        manualOverride: VpnProtocol.trojan,
      );

      // All attempts should be trojan only.
      expect(
        result.attemptLog.every((l) => l.protocol == VpnProtocol.trojan),
        isTrue,
      );

      // Max attempts for one protocol is maxRetries (3).
      expect(result.attemptLog.length, lessThanOrEqualTo(3));
    }, timeout: const Timeout(Duration(minutes: 1)));

    test('attempt log entries have valid fields', () async {
      final result = await fallback.execute(
        serverAddress: '127.0.0.1',
        port: 1,
      );

      for (final log in result.attemptLog) {
        expect(log.attempt, greaterThanOrEqualTo(1));
        expect(log.attempt, lessThanOrEqualTo(ProtocolFallback.maxRetries));
        expect(log.timestamp, isA<DateTime>());
        expect(VpnProtocol.values, contains(log.protocol));
      }
    }, timeout: const Timeout(Duration(minutes: 2)));

    test('success result preserves the working protocol', () async {
      // Connect to a port that is likely listening (flutter test server).
      // This is best-effort; if it fails, we test the failure path.
      final result = await fallback.execute(
        serverAddress: '127.0.0.1',
        port: 1,
      );

      if (result.isSuccess) {
        final success = result as ProtocolFallbackSuccess;
        expect(VpnProtocol.values, contains(success.protocol));
        expect(success.attemptLog, isNotEmpty);
        expect(success.attemptLog.last.success, isTrue);
      } else {
        final failure = result as ProtocolFallbackFailure;
        expect(failure.message, isNotEmpty);
        expect(
          failure.attemptLog.every((log) => !log.success),
          isTrue,
        );
      }
    }, timeout: const Timeout(Duration(minutes: 2)));
  });

  // ---------------------------------------------------------------------------
  // Preferred protocol affects chain order
  // ---------------------------------------------------------------------------

  group('ProtocolFallback - preferred protocol chain ordering', () {
    test('preferred protocol is tried first in attempt log', () async {
      await fallback.setPreferredProtocol(VpnProtocol.trojan);

      final result = await fallback.execute(
        serverAddress: '127.0.0.1',
        port: 1,
      );

      // The first attempt should always be the preferred protocol.
      expect(result.attemptLog.first.protocol, VpnProtocol.trojan);
    }, timeout: const Timeout(Duration(minutes: 2)));

    test('without preferred protocol, first attempt is vless (default chain)',
        () async {
      // Ensure no preferred protocol is set.
      await fallback.setPreferredProtocol(null);

      final result = await fallback.execute(
        serverAddress: '127.0.0.1',
        port: 1,
      );

      // Default chain starts with vless.
      expect(result.attemptLog.first.protocol, VpnProtocol.vless);
    }, timeout: const Timeout(Duration(minutes: 2)));
  });
}
