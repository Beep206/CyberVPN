import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/shared/services/version_service.dart';

// Mocks
class MockApiClient extends Mock implements ApiClient {}

class MockSharedPreferences extends Mock implements SharedPreferences {}

void main() {
  late VersionService versionService;
  late MockApiClient mockApiClient;
  late SharedPreferences mockPrefs;

  setUp(() {
    mockApiClient = MockApiClient();
    mockPrefs = MockSharedPreferences();
    versionService = VersionService(
      apiClient: mockApiClient,
      prefs: mockPrefs,
    );

    // Set up PackageInfo for testing
    PackageInfo.setMockInitialValues(
      appName: 'CyberVPN',
      packageName: 'com.cybervpn.mobile',
      version: '1.0.0',
      buildNumber: '1',
      buildSignature: '',
    );
  });

  group('VersionService - version comparison logic', () {
    test('should identify major version update as mandatory (1.0.0 vs 2.0.0)',
        () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '2.0.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      expect(result!.needsUpdate, isTrue);
      expect(result.isMandatory, isTrue);
      expect(result.currentVersion, '1.0.0');
      expect(result.latestVersion, '2.0.0');
    });

    test('should identify minor version update as optional (1.0.0 vs 1.1.0)',
        () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.1.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      expect(result!.needsUpdate, isTrue);
      expect(result.isMandatory, isFalse);
      expect(result.currentVersion, '1.0.0');
      expect(result.latestVersion, '1.1.0');
    });

    test('should identify patch version update as optional (1.0.0 vs 1.0.1)',
        () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.0.1'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      expect(result!.needsUpdate, isTrue);
      expect(result.isMandatory, isFalse);
      expect(result.currentVersion, '1.0.0');
      expect(result.latestVersion, '1.0.1');
    });

    test('should return needsUpdate=false when versions match', () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.0.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      expect(result!.needsUpdate, isFalse);
      expect(result.isMandatory, isFalse);
    });

    test('should handle current version newer than backend (dev/beta)',
        () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '0.9.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      expect(result!.needsUpdate, isFalse);
    });

    test('should handle version strings with pre-release tags', () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.1.0-beta'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      expect(result!.needsUpdate, isTrue);
      expect(result.latestVersion, '1.1.0-beta');
    });
  });

  group('VersionService - rate limiting', () {
    test('should skip check if called within 1 hour', () async {
      // Arrange - last check was 30 minutes ago
      final thirtyMinutesAgo =
          DateTime.now().subtract(const Duration(minutes: 30));
      when(() => mockPrefs.getInt(any()))
          .thenReturn(thirtyMinutesAgo.millisecondsSinceEpoch);

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNull);
      verifyNever(() => mockApiClient.get<Map<String, dynamic>>(any()));
    });

    test('should perform check if more than 1 hour has passed', () async {
      // Arrange - last check was 2 hours ago
      final twoHoursAgo = DateTime.now().subtract(const Duration(hours: 2));
      when(() => mockPrefs.getInt(any()))
          .thenReturn(twoHoursAgo.millisecondsSinceEpoch);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.0.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      verify(() => mockApiClient.get<Map<String, dynamic>>(any())).called(1);
    });

    test('should perform check if never checked before', () async {
      // Arrange - no last check timestamp
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.0.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNotNull);
      verify(() => mockApiClient.get<Map<String, dynamic>>(any())).called(1);
    });

    test('should bypass rate limiting when force=true', () async {
      // Arrange - last check was 30 minutes ago
      final thirtyMinutesAgo =
          DateTime.now().subtract(const Duration(minutes: 30));
      when(() => mockPrefs.getInt(any()))
          .thenReturn(thirtyMinutesAgo.millisecondsSinceEpoch);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.0.0'},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate(force: true);

      // Assert
      expect(result, isNotNull);
      verify(() => mockApiClient.get<Map<String, dynamic>>(any())).called(1);
    });

    test('should update last check timestamp after successful check',
        () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockPrefs.setInt(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': '1.0.0'},
                statusCode: 200,
              ));

      // Act
      await versionService.checkForUpdate();

      // Assert
      verify(() => mockPrefs.setInt(any(), any())).called(1);
    });
  });

  group('VersionService - error handling', () {
    test('should return null when API call fails', () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenThrow(Exception('Network error'));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNull);
    });

    test('should return null when backend returns null data', () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: null,
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNull);
    });

    test('should return null when backend returns invalid version format',
        () async {
      // Arrange
      when(() => mockPrefs.getInt(any())).thenReturn(null);
      when(() => mockApiClient.get<Map<String, dynamic>>(any()))
          .thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: ''),
                data: {'version': null},
                statusCode: 200,
              ));

      // Act
      final result = await versionService.checkForUpdate();

      // Assert
      expect(result, isNull);
    });
  });

  group('VersionService - UpdateStatus', () {
    test('UpdateStatus toString should include all fields', () {
      // Arrange
      const status = UpdateStatus(
        needsUpdate: true,
        isMandatory: true,
        currentVersion: '1.0.0',
        latestVersion: '2.0.0',
      );

      // Act
      final result = status.toString();

      // Assert
      expect(result, contains('needsUpdate: true'));
      expect(result, contains('isMandatory: true'));
      expect(result, contains('current: 1.0.0'));
      expect(result, contains('latest: 2.0.0'));
    });
  });
}
