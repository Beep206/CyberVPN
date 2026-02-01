import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/security/device_integrity.dart';

class MockSharedPreferences extends Mock implements SharedPreferences {}

void main() {
  late MockSharedPreferences mockPrefs;
  late DeviceIntegrityChecker integrityChecker;

  setUp(() {
    mockPrefs = MockSharedPreferences();
    integrityChecker = DeviceIntegrityChecker(mockPrefs);
  });

  group('DeviceIntegrityChecker', () {
    group('hasUserDismissedWarning', () {
      test('returns false when preference is not set', () async {
        // Arrange
        when(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .thenReturn(null);

        // Act
        final result = await integrityChecker.hasUserDismissedWarning();

        // Assert
        expect(result, false);
        verify(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .called(1);
      });

      test('returns true when preference is set to true', () async {
        // Arrange
        when(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .thenReturn(true);

        // Act
        final result = await integrityChecker.hasUserDismissedWarning();

        // Assert
        expect(result, true);
        verify(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .called(1);
      });

      test('returns false when preference is set to false', () async {
        // Arrange
        when(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .thenReturn(false);

        // Act
        final result = await integrityChecker.hasUserDismissedWarning();

        // Assert
        expect(result, false);
        verify(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .called(1);
      });

      test('returns false on error', () async {
        // Arrange
        when(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .thenThrow(Exception('Storage error'));

        // Act
        final result = await integrityChecker.hasUserDismissedWarning();

        // Assert
        expect(result, false);
        verify(() => mockPrefs.getBool('device_rooted_warning_dismissed'))
            .called(1);
      });
    });

    group('dismissWarning', () {
      test('saves dismissal preference', () async {
        // Arrange
        when(() => mockPrefs.setBool('device_rooted_warning_dismissed', true))
            .thenAnswer((_) async => true);

        // Act
        await integrityChecker.dismissWarning();

        // Assert
        verify(() => mockPrefs.setBool('device_rooted_warning_dismissed', true))
            .called(1);
      });

      test('handles error gracefully', () async {
        // Arrange
        when(() => mockPrefs.setBool('device_rooted_warning_dismissed', true))
            .thenThrow(Exception('Storage error'));

        // Act & Assert - should not throw
        await expectLater(
          integrityChecker.dismissWarning(),
          completes,
        );
        verify(() => mockPrefs.setBool('device_rooted_warning_dismissed', true))
            .called(1);
      });
    });

    group('resetDismissal', () {
      test('removes dismissal preference', () async {
        // Arrange
        when(() => mockPrefs.remove('device_rooted_warning_dismissed'))
            .thenAnswer((_) async => true);

        // Act
        await integrityChecker.resetDismissal();

        // Assert
        verify(() => mockPrefs.remove('device_rooted_warning_dismissed'))
            .called(1);
      });

      test('handles error gracefully', () async {
        // Arrange
        when(() => mockPrefs.remove('device_rooted_warning_dismissed'))
            .thenThrow(Exception('Storage error'));

        // Act & Assert - should not throw
        await expectLater(
          integrityChecker.resetDismissal(),
          completes,
        );
        verify(() => mockPrefs.remove('device_rooted_warning_dismissed'))
            .called(1);
      });
    });

    // Note: isDeviceRooted() cannot be easily unit tested without mocking
    // the flutter_jailbreak_detection plugin. This should be tested via
    // integration tests on actual devices or emulators with root detection
    // capabilities.
  });
}
