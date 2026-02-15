import 'dart:convert';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/profile_local_ds.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/datasources/subscription_fetcher.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/fetch_result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/parsed_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/repositories/profile_repository_impl.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/security/encrypted_field.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/subscription_info.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:drift/drift.dart' show Value;
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ── Mocks ───────────────────────────────────────────────────────────

class MockProfileLocalDataSource extends Mock
    implements ProfileLocalDataSource {}

class MockSubscriptionFetcher extends Mock implements SubscriptionFetcher {}

class MockEncryptedFieldService extends Mock implements EncryptedFieldService {}

class FakeProfilesCompanion extends Fake implements ProfilesCompanion {}

class FakeProfileConfigsCompanion extends Fake
    implements ProfileConfigsCompanion {}

// ── Test Data ───────────────────────────────────────────────────────

const _testUrl = 'https://sub.example.com/token123';
const _encryptedUrl = 'encrypted_url_base64';

final _testProfile = Profile(
  id: 'profile-1',
  name: 'Test Sub',
  type: ProfileType.remote,
  subscriptionUrl: _encryptedUrl,
  isActive: false,
  sortOrder: 0,
  createdAt: DateTime(2026, 1, 1),
  lastUpdatedAt: DateTime(2026, 1, 1),
  uploadBytes: 1000,
  downloadBytes: 5000,
  totalBytes: 100000,
  expiresAt: DateTime(2026, 12, 31),
  updateIntervalMinutes: 60,
  supportUrl: 'https://support.example.com',
  testUrl: null,
);

final _testConfig = ProfileConfig(
  id: 'config-1',
  profileId: 'profile-1',
  name: 'VLESS Server',
  serverAddress: 'vless.example.com',
  port: 443,
  protocol: 'vless',
  configData: jsonEncode({'uuid': 'test-uuid'}),
  remark: null,
  isFavorite: false,
  sortOrder: 0,
  latencyMs: null,
  createdAt: DateTime(2026, 1, 1),
);

final _testFetchResult = FetchResult(
  info: SubscriptionInfo(
    title: 'Test Sub',
    uploadBytes: 1000,
    downloadBytes: 5000,
    totalBytes: 100000,
    expiresAt: DateTime(2026, 12, 31),
    updateIntervalMinutes: 60,
    supportUrl: 'https://support.example.com',
  ),
  servers: const [
    ParsedServer(
      name: 'VLESS Server',
      rawUri: 'vless://test@vless.example.com:443',
      protocol: 'vless',
      serverAddress: 'vless.example.com',
      port: 443,
      configData: {'uuid': 'test-uuid'},
    ),
    ParsedServer(
      name: 'Trojan Server',
      rawUri: 'trojan://pass@trojan.example.com:443',
      protocol: 'trojan',
      serverAddress: 'trojan.example.com',
      port: 443,
      configData: {'password': 'pass'},
    ),
  ],
);

// ── Tests ───────────────────────────────────────────────────────────

void main() {
  late MockProfileLocalDataSource mockLocalDs;
  late MockSubscriptionFetcher mockFetcher;
  late MockEncryptedFieldService mockEncField;
  late ProfileRepositoryImpl repo;

  setUpAll(() {
    registerFallbackValue(FakeProfilesCompanion());
    registerFallbackValue(FakeProfileConfigsCompanion());
    registerFallbackValue(<ProfileConfigsCompanion>[]);
  });

  setUp(() {
    mockLocalDs = MockProfileLocalDataSource();
    mockFetcher = MockSubscriptionFetcher();
    mockEncField = MockEncryptedFieldService();
    repo = ProfileRepositoryImpl(
      localDataSource: mockLocalDs,
      subscriptionFetcher: mockFetcher,
      encryptedField: mockEncField,
    );
  });

  group('getById', () {
    test('returns Success with profile when found', () async {
      when(() => mockLocalDs.getById('profile-1'))
          .thenAnswer((_) async => _testProfile);
      when(() => mockLocalDs.getConfigsByProfileId('profile-1'))
          .thenAnswer((_) async => [_testConfig]);

      final result = await repo.getById('profile-1');

      expect(result.isSuccess, isTrue);
      final profile = (result as Success<VpnProfile>).data;
      expect(profile.id, 'profile-1');
      expect(profile.name, 'Test Sub');
      expect(profile, isA<RemoteVpnProfile>());
    });

    test('returns Failure when profile not found', () async {
      when(() => mockLocalDs.getById('missing'))
          .thenAnswer((_) async => null);

      final result = await repo.getById('missing');

      expect(result.isFailure, isTrue);
    });
  });

  group('addRemoteProfile', () {
    test('creates profile with fetched servers on success', () async {
      when(() => mockFetcher.fetch(_testUrl))
          .thenAnswer((_) async => _testFetchResult);
      when(() => mockEncField.encrypt(_testUrl))
          .thenAnswer((_) async => _encryptedUrl);
      when(() => mockLocalDs.insert(any()))
          .thenAnswer((_) async => _testProfile);
      when(() => mockLocalDs.insertConfigs(any()))
          .thenAnswer((_) async {});
      when(() => mockLocalDs.getById(any()))
          .thenAnswer((_) async => _testProfile);
      when(() => mockLocalDs.getConfigsByProfileId(any()))
          .thenAnswer((_) async => [_testConfig]);

      final result = await repo.addRemoteProfile(_testUrl, name: 'My Sub');

      expect(result.isSuccess, isTrue);
      verify(() => mockFetcher.fetch(_testUrl)).called(1);
      verify(() => mockEncField.encrypt(_testUrl)).called(1);
      verify(() => mockLocalDs.insert(any())).called(1);
      verify(() => mockLocalDs.insertConfigs(any())).called(1);
    });

    test('returns Failure when no servers found', () async {
      when(() => mockFetcher.fetch(_testUrl)).thenAnswer(
        (_) async => const FetchResult(
          info: SubscriptionInfo(),
          servers: [],
        ),
      );

      final result = await repo.addRemoteProfile(_testUrl);

      expect(result.isFailure, isTrue);
    });

    test('returns Failure on network error', () async {
      when(() => mockFetcher.fetch(_testUrl)).thenThrow(
        const SubscriptionFetcherException(
          url: _testUrl,
          message: 'timeout',
        ),
      );

      final result = await repo.addRemoteProfile(_testUrl);

      expect(result.isFailure, isTrue);
    });
  });

  group('addLocalProfile', () {
    test('creates local profile with provided servers', () async {
      when(() => mockLocalDs.insert(any()))
          .thenAnswer((_) async => _testProfile);
      when(() => mockLocalDs.insertConfigs(any()))
          .thenAnswer((_) async {});
      when(() => mockLocalDs.getById(any()))
          .thenAnswer((_) async => _testProfile.copyWith(type: ProfileType.local));
      when(() => mockLocalDs.getConfigsByProfileId(any()))
          .thenAnswer((_) async => [_testConfig]);

      final servers = [
        ProfileServer(
          id: 'srv-1',
          profileId: 'temp',
          name: 'My Server',
          serverAddress: 'server.example.com',
          port: 443,
          protocol: VpnProtocol.vless,
          configData: '{}',
          sortOrder: 0,
          createdAt: DateTime(2026, 1, 1),
        ),
      ];

      final result = await repo.addLocalProfile('Local Profile', servers);

      expect(result.isSuccess, isTrue);
      verify(() => mockLocalDs.insert(any())).called(1);
      verify(() => mockLocalDs.insertConfigs(any())).called(1);
    });
  });

  group('setActive', () {
    test('delegates to local data source', () async {
      when(() => mockLocalDs.setActive('profile-1'))
          .thenAnswer((_) async {});

      final result = await repo.setActive('profile-1');

      expect(result.isSuccess, isTrue);
      verify(() => mockLocalDs.setActive('profile-1')).called(1);
    });
  });

  group('delete', () {
    test('returns Success on successful delete', () async {
      when(() => mockLocalDs.delete('profile-1'))
          .thenAnswer((_) async => 1);

      final result = await repo.delete('profile-1');

      expect(result.isSuccess, isTrue);
      verify(() => mockLocalDs.delete('profile-1')).called(1);
    });

    test('returns Failure on exception', () async {
      when(() => mockLocalDs.delete('profile-1'))
          .thenThrow(Exception('DB error'));

      final result = await repo.delete('profile-1');

      expect(result.isFailure, isTrue);
    });
  });

  group('updateSubscription', () {
    test('refreshes remote profile servers', () async {
      when(() => mockLocalDs.getById('profile-1'))
          .thenAnswer((_) async => _testProfile);
      when(() => mockEncField.decrypt(_encryptedUrl))
          .thenAnswer((_) async => _testUrl);
      when(() => mockFetcher.fetch(_testUrl))
          .thenAnswer((_) async => _testFetchResult);
      when(() => mockLocalDs.update(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockLocalDs.replaceConfigs(any(), any()))
          .thenAnswer((_) async {});

      final result = await repo.updateSubscription('profile-1');

      expect(result.isSuccess, isTrue);
      verify(() => mockFetcher.fetch(_testUrl)).called(1);
      verify(() => mockLocalDs.replaceConfigs('profile-1', any())).called(1);
    });

    test('returns Failure when profile not found', () async {
      when(() => mockLocalDs.getById('missing'))
          .thenAnswer((_) async => null);

      final result = await repo.updateSubscription('missing');

      expect(result.isFailure, isTrue);
    });

    test('returns Failure for local profile', () async {
      when(() => mockLocalDs.getById('local-1'))
          .thenAnswer((_) async => _testProfile.copyWith(type: ProfileType.local));

      final result = await repo.updateSubscription('local-1');

      expect(result.isFailure, isTrue);
    });

    test('returns Failure on network error', () async {
      when(() => mockLocalDs.getById('profile-1'))
          .thenAnswer((_) async => _testProfile);
      when(() => mockEncField.decrypt(_encryptedUrl))
          .thenAnswer((_) async => _testUrl);
      when(() => mockFetcher.fetch(_testUrl)).thenThrow(
        const SubscriptionFetcherException(
          url: _testUrl,
          message: 'Network error',
        ),
      );

      final result = await repo.updateSubscription('profile-1');

      expect(result.isFailure, isTrue);
    });
  });

  group('updateAllDueSubscriptions', () {
    test('updates profiles past their interval', () async {
      final staleProfile = _testProfile.copyWith(
        lastUpdatedAt: Value(DateTime.now().subtract(const Duration(hours: 2))),
      );

      when(() => mockLocalDs.watchAll())
          .thenAnswer((_) => Stream.value([staleProfile]));
      when(() => mockLocalDs.getById('profile-1'))
          .thenAnswer((_) async => staleProfile);
      when(() => mockEncField.decrypt(_encryptedUrl))
          .thenAnswer((_) async => _testUrl);
      when(() => mockFetcher.fetch(_testUrl))
          .thenAnswer((_) async => _testFetchResult);
      when(() => mockLocalDs.update(any(), any()))
          .thenAnswer((_) async => true);
      when(() => mockLocalDs.replaceConfigs(any(), any()))
          .thenAnswer((_) async {});

      final result = await repo.updateAllDueSubscriptions();

      expect(result.isSuccess, isTrue);
      expect((result as Success<int>).data, 1);
    });

    test('skips profiles within their interval', () async {
      final freshProfile = _testProfile.copyWith(
        lastUpdatedAt: Value(DateTime.now().subtract(const Duration(minutes: 5))),
      );

      when(() => mockLocalDs.watchAll())
          .thenAnswer((_) => Stream.value([freshProfile]));

      final result = await repo.updateAllDueSubscriptions();

      expect(result.isSuccess, isTrue);
      expect((result as Success<int>).data, 0);
      verifyNever(() => mockFetcher.fetch(any()));
    });
  });

  group('count', () {
    test('returns count from data source', () async {
      when(() => mockLocalDs.count()).thenAnswer((_) async => 5);

      final result = await repo.count();

      expect(result.isSuccess, isTrue);
      expect((result as Success<int>).data, 5);
    });
  });

  group('reorder', () {
    test('updates sort orders for all profile IDs', () async {
      when(() => mockLocalDs.updateSortOrders(any()))
          .thenAnswer((_) async {});

      final result = await repo.reorder(['b', 'a', 'c']);

      expect(result.isSuccess, isTrue);
      verify(
        () => mockLocalDs.updateSortOrders({'b': 0, 'a': 1, 'c': 2}),
      ).called(1);
    });
  });
}
