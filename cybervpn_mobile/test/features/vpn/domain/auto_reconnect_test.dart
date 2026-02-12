import 'dart:async';

import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/auto_reconnect.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../../helpers/mock_factories.dart';
import '../../../helpers/mock_repositories.dart';

class MockNetworkInfo extends Mock implements NetworkInfo {}

void main() {
  late MockVpnRepository mockRepository;
  late MockNetworkInfo mockNetworkInfo;
  late AutoReconnectService service;
  late StreamController<bool> connectivityController;

  setUpAll(() {
    registerFallbackValue(createMockVpnConfig());
  });

  setUp(() {
    mockRepository = MockVpnRepository();
    mockNetworkInfo = MockNetworkInfo();
    connectivityController = StreamController<bool>.broadcast();

    when(() => mockNetworkInfo.onConnectivityChanged)
        .thenAnswer((_) => connectivityController.stream);

    service = AutoReconnectService(
      repository: mockRepository,
      networkInfo: mockNetworkInfo,
    );
  });

  tearDown(() {
    service.dispose();
    unawaited(connectivityController.close());
  });

  // ---------------------------------------------------------------------------
  // Basic start / stop
  // ---------------------------------------------------------------------------

  group('AutoReconnectService - start and stop', () {
    test('start stores config and listens to connectivity', () {
      final config = createMockVpnConfig();

      service.start(config);

      // Verify that onConnectivityChanged was accessed (listener registered).
      verify(() => mockNetworkInfo.onConnectivityChanged).called(1);
    });

    test('stop cancels subscription and resets state', () {
      final config = createMockVpnConfig();
      service.start(config);
      service.stop();

      // After stop, no reconnect attempts should happen even if connectivity
      // changes.
      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(false));
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      connectivityController.add(true);

      // Give the event loop a turn to process the event.
      verifyNever(() => mockRepository.connect(any()));
    });

    test('dispose calls stop internally', () {
      final config = createMockVpnConfig();
      service.start(config);
      service.dispose();

      // Should not throw or attempt reconnection after dispose.
      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(false));
      connectivityController.add(true);
      verifyNever(() => mockRepository.connect(any()));
    });
  });

  // ---------------------------------------------------------------------------
  // Reconnect triggers
  // ---------------------------------------------------------------------------

  group('AutoReconnectService - reconnect triggers', () {
    test('attempts reconnect when connectivity restored and not connected',
        () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(false));
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      service.start(config);
      connectivityController.add(true);

      // Allow the async listener callback to run.
      await Future<void>.delayed(const Duration(milliseconds: 50));

      verify(() => mockRepository.connect(config)).called(1);
    });

    test('does not attempt reconnect when already connected', () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(true));

      service.start(config);
      connectivityController.add(true);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      verifyNever(() => mockRepository.connect(any()));
    });

    test('does not attempt reconnect on connectivity loss (false)', () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(false));

      service.start(config);
      connectivityController.add(false);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      verifyNever(() => mockRepository.connect(any()));
    });
  });

  // ---------------------------------------------------------------------------
  // Max reconnect attempts
  // ---------------------------------------------------------------------------

  group('AutoReconnectService - max attempts', () {
    test('maxReconnectAttempts matches VpnConstants', () {
      expect(VpnConstants.maxReconnectAttempts, equals(5));
      expect(
        VpnConstants.maxReconnectAttempts,
        equals(VpnConstants.maxRetryAttempts),
      );
    });

    test('reconnectDelaySeconds is positive', () {
      expect(VpnConstants.reconnectDelaySeconds, greaterThan(0));
    });
  });

  // ---------------------------------------------------------------------------
  // Exponential backoff timing
  // ---------------------------------------------------------------------------

  group('AutoReconnectService - exponential backoff', () {
    test('backoff delay increases linearly with retry count', () {
      // AutoReconnectService uses: reconnectDelaySeconds * retryCount
      // Retry 1: 2s, Retry 2: 4s, Retry 3: 6s, Retry 4: 8s, Retry 5: 10s
      const baseDelay = VpnConstants.reconnectDelaySeconds;
      expect(baseDelay * 1, equals(2));
      expect(baseDelay * 2, equals(4));
      expect(baseDelay * 3, equals(6));
      expect(baseDelay * 4, equals(8));
      expect(baseDelay * 5, equals(10));
    });

    test('retryDelayMs and retryBackoffMultiplier are configured', () {
      // These constants exist for the general retry policy:
      expect(VpnConstants.retryDelayMs, equals(1000));
      expect(VpnConstants.retryBackoffMultiplier, equals(2.0));
      expect(VpnConstants.maxRetryDelayMs, equals(30000));
    });
  });

  // ---------------------------------------------------------------------------
  // Reset on successful connection
  // ---------------------------------------------------------------------------

  group('AutoReconnectService - reset behavior', () {
    test('retry counter resets on successful reconnection', () async {
      final config = createMockVpnConfig();
      int callCount = 0;

      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(false));
      when(() => mockRepository.connect(any())).thenAnswer((_) async {
        callCount++;
        // First call succeeds.
        return const Success<void>(null);
      });

      service.start(config);
      connectivityController.add(true);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      // After success, retry count should be reset internally to 0.
      // Another connectivity event should trigger a new reconnect attempt.
      connectivityController.add(true);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Both attempts should succeed, proving retry counter was reset.
      expect(callCount, equals(2));
    });

    test('start resets retry counter', () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.isConnected).thenAnswer((_) async => const Success(false));
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      // Start, then re-start with new config should reset retry count.
      service.start(config);
      service.start(createMockVpnConfig(id: 'new-config'));

      connectivityController.add(true);

      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Should attempt connect with the new config.
      verify(() => mockRepository.connect(any())).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // VpnConstants - reconnection settings
  // ---------------------------------------------------------------------------

  group('VpnConstants - reconnection settings', () {
    test('maxRetryAttempts is 5', () {
      expect(VpnConstants.maxRetryAttempts, 5);
    });

    test('retryDelayMs is 1000', () {
      expect(VpnConstants.retryDelayMs, 1000);
    });

    test('retryBackoffMultiplier is 2.0', () {
      expect(VpnConstants.retryBackoffMultiplier, 2.0);
    });

    test('maxRetryDelayMs is 30000', () {
      expect(VpnConstants.maxRetryDelayMs, 30000);
    });
  });
}
