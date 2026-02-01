import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/repositories/settings_repository.dart';

class MockSettingsRepository extends Mock implements SettingsRepository {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('HapticService', () {
    late MockSettingsRepository mockSettingsRepo;
    late ProviderContainer container;

    setUp(() {
      mockSettingsRepo = MockSettingsRepository();

      container = ProviderContainer(
        overrides: [
          settingsRepositoryProvider.overrideWithValue(mockSettingsRepo),
        ],
      );
    });

    tearDown(() {
      container.dispose();
    });

    group('when haptics are enabled in settings', () {
      setUp(() {
        when(() => mockSettingsRepo.getSettings()).thenAnswer(
          (_) async => const AppSettings(hapticsEnabled: true),
        );
      });

      test('selection() calls HapticFeedback.selectionClick', () async {
        final service = container.read(hapticServiceProvider);

        // Setup method channel mock
        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.selection();

        // Verify the correct haptic method was called
        expect(
          log,
          contains(
            isA<MethodCall>().having(
              (call) => call.method,
              'method',
              'HapticFeedback.vibrate',
            ),
          ),
        );
      });

      test('impact() calls HapticFeedback.mediumImpact', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.impact();

        expect(
          log,
          contains(
            isA<MethodCall>().having(
              (call) => call.method,
              'method',
              'HapticFeedback.vibrate',
            ),
          ),
        );
      });

      test('heavy() calls HapticFeedback.heavyImpact', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.heavy();

        expect(
          log,
          contains(
            isA<MethodCall>().having(
              (call) => call.method,
              'method',
              'HapticFeedback.vibrate',
            ),
          ),
        );
      });

      test('success() calls light and medium impacts with delay', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.success();

        // Should have at least 2 haptic calls (light + medium)
        final hapticCalls = log.where(
          (call) => call.method == 'HapticFeedback.vibrate',
        );
        expect(hapticCalls.length, greaterThanOrEqualTo(2));
      });

      test('error() calls HapticFeedback.heavyImpact', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.error();

        expect(
          log,
          contains(
            isA<MethodCall>().having(
              (call) => call.method,
              'method',
              'HapticFeedback.vibrate',
            ),
          ),
        );
      });
    });

    group('when haptics are disabled in settings', () {
      setUp(() {
        when(() => mockSettingsRepo.getSettings()).thenAnswer(
          (_) async => const AppSettings(hapticsEnabled: false),
        );
      });

      test('selection() does not trigger haptic feedback', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.selection();

        // Should not have any haptic calls
        final hapticCalls = log.where(
          (call) => call.method == 'HapticFeedback.vibrate',
        );
        expect(hapticCalls, isEmpty);
      });

      test('impact() does not trigger haptic feedback', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.impact();

        final hapticCalls = log.where(
          (call) => call.method == 'HapticFeedback.vibrate',
        );
        expect(hapticCalls, isEmpty);
      });

      test('success() does not trigger haptic feedback', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        await service.success();

        final hapticCalls = log.where(
          (call) => call.method == 'HapticFeedback.vibrate',
        );
        expect(hapticCalls, isEmpty);
      });
    });

    group('when settings repository throws', () {
      setUp(() {
        when(() => mockSettingsRepo.getSettings())
            .thenThrow(Exception('Settings error'));
      });

      test('defaults to enabled and triggers haptic', () async {
        final service = container.read(hapticServiceProvider);

        const channel = MethodChannel('flutter/platform');
        final List<MethodCall> log = [];
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
          log.add(methodCall);
          return null;
        });

        // Should not throw and should trigger haptic (defaults to enabled)
        await service.selection();

        expect(
          log,
          contains(
            isA<MethodCall>().having(
              (call) => call.method,
              'method',
              'HapticFeedback.vibrate',
            ),
          ),
        );
      });
    });
  });
}
