import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/services/legacy_profile_migration.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

import '../../../../helpers/fakes/fake_local_storage.dart';
import '../../../../helpers/mock_factories.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockConfigImportRepo extends Mock implements ConfigImportRepository {}

class MockVpnProfileRepo extends Mock implements ProfileRepository {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Creates a fake local profile returned by addLocalProfile.
VpnProfile _fakeLocalProfile({
  String id = 'profile-001',
  String name = 'CyberVPN',
  List<ProfileServer> servers = const [],
}) {
  return VpnProfile.local(
    id: id,
    name: name,
    isActive: false,
    sortOrder: 0,
    createdAt: DateTime(2026, 1, 1),
    servers: servers,
  );
}

/// Creates a list of legacy imported configs for testing.
List<ImportedConfig> _legacyConfigs() {
  return [
    createMockImportedConfig(
      id: 'legacy-1',
      name: 'US Server',
      protocol: 'vless',
      serverAddress: '203.0.113.1',
      port: 443,
      rawUri: 'vless://uuid@203.0.113.1:443',
    ),
    createMockImportedConfig(
      id: 'legacy-2',
      name: 'DE Server',
      protocol: 'vmess',
      serverAddress: '203.0.113.2',
      port: 8443,
      rawUri: 'vmess://uuid@203.0.113.2:8443',
    ),
    createMockImportedConfig(
      id: 'legacy-3',
      name: 'JP Server',
      protocol: 'trojan',
      serverAddress: '203.0.113.3',
      port: 443,
      rawUri: 'trojan://password@203.0.113.3:443',
    ),
  ];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockConfigImportRepo configImportRepo;
  late MockVpnProfileRepo profileRepo;
  late FakeLocalStorage localStorage;
  late LegacyProfileMigrationService service;

  setUp(() {
    configImportRepo = MockConfigImportRepo();
    profileRepo = MockVpnProfileRepo();
    localStorage = FakeLocalStorage();

    service = LegacyProfileMigrationService(
      configImportRepository: configImportRepo,
      profileRepository: profileRepo,
      localStorage: localStorage,
    );

    // Register fallback values for mocktail any() matchers.
    registerFallbackValue(<ProfileServer>[]);
  });

  group('LegacyProfileMigrationService', () {
    // -----------------------------------------------------------------
    // Happy path: first launch with legacy data
    // -----------------------------------------------------------------
    group('first launch with legacy configs', () {
      test('creates local profile named "CyberVPN"', () async {
        final configs = _legacyConfigs();
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        final result = await service.migrate();

        expect(result, isTrue);

        // Verify addLocalProfile was called with "CyberVPN" and 3 servers.
        final captured = verify(
          () => profileRepo.addLocalProfile(
            captureAny(),
            captureAny(),
          ),
        ).captured;

        expect(captured[0], 'CyberVPN');
        final servers = captured[1] as List<ProfileServer>;
        expect(servers, hasLength(3));
      });

      test('maps imported configs to ProfileServer correctly', () async {
        final configs = _legacyConfigs();
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final captured = verify(
          () => profileRepo.addLocalProfile(any(), captureAny()),
        ).captured;

        final servers = captured[0] as List<ProfileServer>;

        // First server: vless
        expect(servers[0].name, 'US Server');
        expect(servers[0].serverAddress, '203.0.113.1');
        expect(servers[0].port, 443);
        expect(servers[0].protocol, VpnProtocol.vless);
        expect(servers[0].configData, 'vless://uuid@203.0.113.1:443');
        expect(servers[0].sortOrder, 0);

        // Second server: vmess
        expect(servers[1].name, 'DE Server');
        expect(servers[1].protocol, VpnProtocol.vmess);
        expect(servers[1].sortOrder, 1);

        // Third server: trojan
        expect(servers[2].name, 'JP Server');
        expect(servers[2].protocol, VpnProtocol.trojan);
        expect(servers[2].sortOrder, 2);
      });

      test('sets created profile as active', () async {
        final profile = _fakeLocalProfile(id: 'new-profile-id');
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(profile));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        verify(() => profileRepo.setActive('new-profile-id')).called(1);
      });

      test('sets migration flag after success', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final flag = await localStorage.getBool(
          LocalStorageWrapper.profileMigrationV1CompleteKey,
        );
        expect(flag, isTrue);
      });

      test('returns true when migration performed', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        final result = await service.migrate();

        expect(result, isTrue);
      });
    });

    // -----------------------------------------------------------------
    // Idempotency: second launch skips migration
    // -----------------------------------------------------------------
    group('idempotency', () {
      test('skips migration when flag is already set', () async {
        await localStorage.setBool(
          LocalStorageWrapper.profileMigrationV1CompleteKey,
          true,
        );

        final result = await service.migrate();

        expect(result, isFalse);
        verifyNever(() => configImportRepo.getImportedConfigs());
        verifyNever(() => profileRepo.addLocalProfile(any(), any()));
      });

      test('second call after successful migration returns false', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        // First call performs migration.
        final first = await service.migrate();
        expect(first, isTrue);

        // Second call should skip.
        final second = await service.migrate();
        expect(second, isFalse);

        // addLocalProfile should only have been called once.
        verify(() => profileRepo.addLocalProfile(any(), any())).called(1);
      });
    });

    // -----------------------------------------------------------------
    // No legacy data
    // -----------------------------------------------------------------
    group('no legacy configs', () {
      test('marks complete and returns false when no configs exist', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => []);

        final result = await service.migrate();

        expect(result, isFalse);
        verifyNever(() => profileRepo.addLocalProfile(any(), any()));

        // Flag should still be set.
        final flag = await localStorage.getBool(
          LocalStorageWrapper.profileMigrationV1CompleteKey,
        );
        expect(flag, isTrue);
      });
    });

    // -----------------------------------------------------------------
    // Profiles already exist (e.g. fresh install used new UI)
    // -----------------------------------------------------------------
    group('profiles already exist', () {
      test('skips migration when profiles > 0', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(2));

        final result = await service.migrate();

        expect(result, isFalse);
        verifyNever(() => profileRepo.addLocalProfile(any(), any()));

        final flag = await localStorage.getBool(
          LocalStorageWrapper.profileMigrationV1CompleteKey,
        );
        expect(flag, isTrue);
      });

      test('treats count failure as 0 and proceeds', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count()).thenAnswer(
          (_) async =>
              const Failure(CacheFailure(message: 'DB error')),
        );
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        final result = await service.migrate();

        // Should proceed since count failure → 0.
        expect(result, isTrue);
        verify(() => profileRepo.addLocalProfile(any(), any())).called(1);
      });
    });

    // -----------------------------------------------------------------
    // Failure scenarios
    // -----------------------------------------------------------------
    group('failure handling', () {
      test('does not crash when addLocalProfile fails', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any())).thenAnswer(
          (_) async => const Failure(
            CacheFailure(message: 'Disk full'),
          ),
        );

        final result = await service.migrate();

        expect(result, isFalse);
        verifyNever(() => profileRepo.setActive(any()));
      });

      test('does not set flag when addLocalProfile fails', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => _legacyConfigs());
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any())).thenAnswer(
          (_) async => const Failure(
            CacheFailure(message: 'Disk full'),
          ),
        );

        await service.migrate();

        // Flag should NOT be set so retry is possible.
        final flag = await localStorage.getBool(
          LocalStorageWrapper.profileMigrationV1CompleteKey,
        );
        expect(flag, isNull);
      });

      test('does not crash when getImportedConfigs throws', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenThrow(Exception('DB corrupted'));

        final result = await service.migrate();

        expect(result, isFalse);
        verifyNever(() => profileRepo.addLocalProfile(any(), any()));
      });

      test('does not set flag when exception is thrown', () async {
        when(() => configImportRepo.getImportedConfigs())
            .thenThrow(Exception('DB corrupted'));

        await service.migrate();

        final flag = await localStorage.getBool(
          LocalStorageWrapper.profileMigrationV1CompleteKey,
        );
        expect(flag, isNull);
      });
    });

    // -----------------------------------------------------------------
    // Protocol mapping
    // -----------------------------------------------------------------
    group('protocol mapping', () {
      test('maps all known protocol strings correctly', () async {
        final configs = [
          createMockImportedConfig(id: 'c1', protocol: 'vless'),
          createMockImportedConfig(id: 'c2', protocol: 'vmess'),
          createMockImportedConfig(id: 'c3', protocol: 'trojan'),
          createMockImportedConfig(id: 'c4', protocol: 'ss'),
          createMockImportedConfig(id: 'c5', protocol: 'shadowsocks'),
        ];

        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final captured = verify(
          () => profileRepo.addLocalProfile(any(), captureAny()),
        ).captured;

        final servers = captured[0] as List<ProfileServer>;
        expect(servers[0].protocol, VpnProtocol.vless);
        expect(servers[1].protocol, VpnProtocol.vmess);
        expect(servers[2].protocol, VpnProtocol.trojan);
        expect(servers[3].protocol, VpnProtocol.shadowsocks);
        expect(servers[4].protocol, VpnProtocol.shadowsocks);
      });

      test('defaults unknown protocol to vless', () async {
        final configs = [
          createMockImportedConfig(id: 'c1', protocol: 'wireguard'),
        ];

        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final captured = verify(
          () => profileRepo.addLocalProfile(any(), captureAny()),
        ).captured;

        final servers = captured[0] as List<ProfileServer>;
        expect(servers[0].protocol, VpnProtocol.vless);
      });
    });

    // -----------------------------------------------------------------
    // Server field correctness
    // -----------------------------------------------------------------
    group('server field mapping', () {
      test('uses legacy- prefixed IDs', () async {
        final configs = [
          createMockImportedConfig(id: 'abc-123'),
        ];

        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final captured = verify(
          () => profileRepo.addLocalProfile(any(), captureAny()),
        ).captured;

        final servers = captured[0] as List<ProfileServer>;
        expect(servers[0].id, 'legacy-abc-123');
      });

      test('preserves importedAt as createdAt', () async {
        final importDate = DateTime(2025, 6, 15, 10, 30);
        final configs = [
          createMockImportedConfig(id: 'c1', importedAt: importDate),
        ];

        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final captured = verify(
          () => profileRepo.addLocalProfile(any(), captureAny()),
        ).captured;

        final servers = captured[0] as List<ProfileServer>;
        expect(servers[0].createdAt, importDate);
      });

      test('stores rawUri as configData', () async {
        final configs = [
          createMockImportedConfig(
            id: 'c1',
            rawUri: 'vless://special-uuid@host:443',
          ),
        ];

        when(() => configImportRepo.getImportedConfigs())
            .thenAnswer((_) async => configs);
        when(() => profileRepo.count())
            .thenAnswer((_) async => const Success(0));
        when(() => profileRepo.addLocalProfile(any(), any()))
            .thenAnswer((_) async => Success(_fakeLocalProfile()));
        when(() => profileRepo.setActive(any()))
            .thenAnswer((_) async => const Success(null));

        await service.migrate();

        final captured = verify(
          () => profileRepo.addLocalProfile(any(), captureAny()),
        ).captured;

        final servers = captured[0] as List<ProfileServer>;
        expect(servers[0].configData, 'vless://special-uuid@host:443');
      });
    });
  });
}
