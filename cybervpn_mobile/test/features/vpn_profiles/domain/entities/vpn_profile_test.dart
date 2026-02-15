import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final now = DateTime(2026, 2, 15, 12, 0, 0);

  ProfileServer _server({String id = 'srv-1', String profileId = 'p-1'}) {
    return ProfileServer(
      id: id,
      profileId: profileId,
      name: 'US East',
      serverAddress: '203.0.113.1',
      port: 443,
      protocol: VpnProtocol.vless,
      configData: '{"uuid":"test"}',
      sortOrder: 0,
      createdAt: now,
    );
  }

  group('VpnProfile.remote', () {
    late RemoteVpnProfile profile;

    setUp(() {
      profile = VpnProfile.remote(
        id: 'p-remote-1',
        name: 'My Sub',
        subscriptionUrl: 'https://sub.example.com/token',
        sortOrder: 0,
        createdAt: now,
      ) as RemoteVpnProfile;
    });

    test('creates with all required fields', () {
      expect(profile.id, 'p-remote-1');
      expect(profile.name, 'My Sub');
      expect(profile.subscriptionUrl, 'https://sub.example.com/token');
      expect(profile.sortOrder, 0);
      expect(profile.createdAt, now);
    });

    test('defaults are applied correctly', () {
      expect(profile.isActive, false);
      expect(profile.uploadBytes, 0);
      expect(profile.downloadBytes, 0);
      expect(profile.totalBytes, 0);
      expect(profile.updateIntervalMinutes, 60);
      expect(profile.servers, isEmpty);
    });

    test('optional fields default to null', () {
      expect(profile.lastUpdatedAt, isNull);
      expect(profile.expiresAt, isNull);
      expect(profile.supportUrl, isNull);
      expect(profile.testUrl, isNull);
    });

    test('creates with all optional fields', () {
      final expires = DateTime(2026, 3, 15);
      final updated = DateTime(2026, 2, 14);
      final servers = [_server(profileId: 'p-remote-full')];

      final full = VpnProfile.remote(
        id: 'p-remote-full',
        name: 'Full Sub',
        subscriptionUrl: 'https://sub.example.com/full',
        isActive: true,
        sortOrder: 1,
        createdAt: now,
        lastUpdatedAt: updated,
        uploadBytes: 100,
        downloadBytes: 200,
        totalBytes: 1000,
        expiresAt: expires,
        updateIntervalMinutes: 120,
        supportUrl: 'https://support.example.com',
        testUrl: 'https://test.example.com',
        servers: servers,
      ) as RemoteVpnProfile;

      expect(full.isActive, true);
      expect(full.lastUpdatedAt, updated);
      expect(full.uploadBytes, 100);
      expect(full.downloadBytes, 200);
      expect(full.totalBytes, 1000);
      expect(full.expiresAt, expires);
      expect(full.updateIntervalMinutes, 120);
      expect(full.supportUrl, 'https://support.example.com');
      expect(full.testUrl, 'https://test.example.com');
      expect(full.servers, hasLength(1));
    });

    test('copyWith preserves unchanged fields', () {
      final updated = profile.copyWith(name: 'Renamed');

      expect(updated.name, 'Renamed');
      expect(updated.id, profile.id);
      expect(updated.subscriptionUrl, profile.subscriptionUrl);
      expect(updated.isActive, profile.isActive);
      expect(updated.sortOrder, profile.sortOrder);
      expect(updated.createdAt, profile.createdAt);
    });

    test('copyWith updates multiple fields', () {
      final updated = profile.copyWith(
        isActive: true,
        uploadBytes: 500,
        downloadBytes: 1000,
      );

      expect(updated.isActive, true);
      expect(updated.uploadBytes, 500);
      expect(updated.downloadBytes, 1000);
      expect(updated.id, profile.id);
    });

    test('equality for identical remote profiles', () {
      final profile2 = VpnProfile.remote(
        id: 'p-remote-1',
        name: 'My Sub',
        subscriptionUrl: 'https://sub.example.com/token',
        sortOrder: 0,
        createdAt: now,
      );

      expect(profile, equals(profile2));
      expect(profile.hashCode, equals(profile2.hashCode));
    });

    test('inequality when id differs', () {
      final profile2 = VpnProfile.remote(
        id: 'p-remote-different',
        name: 'My Sub',
        subscriptionUrl: 'https://sub.example.com/token',
        sortOrder: 0,
        createdAt: now,
      );

      expect(profile, isNot(equals(profile2)));
    });

    test('inequality between remote and local with same id', () {
      final localProfile = VpnProfile.local(
        id: 'p-remote-1',
        name: 'My Sub',
        sortOrder: 0,
        createdAt: now,
      );

      expect(profile, isNot(equals(localProfile)));
    });

    test('is a VpnProfile', () {
      expect(profile, isA<VpnProfile>());
      expect(profile, isA<RemoteVpnProfile>());
    });

    test('toString contains meaningful info', () {
      final str = profile.toString();
      expect(str, contains('p-remote-1'));
    });
  });

  group('VpnProfile.local', () {
    late LocalVpnProfile profile;

    setUp(() {
      profile = VpnProfile.local(
        id: 'p-local-1',
        name: 'Local Configs',
        sortOrder: 0,
        createdAt: now,
      ) as LocalVpnProfile;
    });

    test('creates with all required fields', () {
      expect(profile.id, 'p-local-1');
      expect(profile.name, 'Local Configs');
      expect(profile.sortOrder, 0);
      expect(profile.createdAt, now);
    });

    test('defaults are applied correctly', () {
      expect(profile.isActive, false);
      expect(profile.servers, isEmpty);
    });

    test('optional fields default to null', () {
      expect(profile.lastUpdatedAt, isNull);
    });

    test('creates with servers and optional fields', () {
      final updated = DateTime(2026, 2, 14);
      final servers = [_server(profileId: 'p-local-full')];

      final full = VpnProfile.local(
        id: 'p-local-full',
        name: 'Full Local',
        isActive: true,
        sortOrder: 2,
        createdAt: now,
        lastUpdatedAt: updated,
        servers: servers,
      ) as LocalVpnProfile;

      expect(full.isActive, true);
      expect(full.lastUpdatedAt, updated);
      expect(full.servers, hasLength(1));
      expect(full.servers.first.profileId, 'p-local-full');
    });

    test('copyWith preserves unchanged fields', () {
      final updated = profile.copyWith(name: 'Renamed Local');

      expect(updated.name, 'Renamed Local');
      expect(updated.id, profile.id);
      expect(updated.isActive, profile.isActive);
      expect(updated.sortOrder, profile.sortOrder);
      expect(updated.createdAt, profile.createdAt);
    });

    test('equality for identical local profiles', () {
      final profile2 = VpnProfile.local(
        id: 'p-local-1',
        name: 'Local Configs',
        sortOrder: 0,
        createdAt: now,
      );

      expect(profile, equals(profile2));
      expect(profile.hashCode, equals(profile2.hashCode));
    });

    test('inequality when name differs', () {
      final profile2 = VpnProfile.local(
        id: 'p-local-1',
        name: 'Different Name',
        sortOrder: 0,
        createdAt: now,
      );

      expect(profile, isNot(equals(profile2)));
    });

    test('is a VpnProfile', () {
      expect(profile, isA<VpnProfile>());
      expect(profile, isA<LocalVpnProfile>());
    });

    test('toString contains meaningful info', () {
      final str = profile.toString();
      expect(str, contains('p-local-1'));
    });
  });

  group('VpnProfile pattern matching', () {
    test('can match remote variant', () {
      final VpnProfile profile = VpnProfile.remote(
        id: 'p-1',
        name: 'Sub',
        subscriptionUrl: 'https://example.com',
        sortOrder: 0,
        createdAt: now,
      );

      final result = switch (profile) {
        RemoteVpnProfile(:final subscriptionUrl) => subscriptionUrl,
        LocalVpnProfile() => 'local',
      };

      expect(result, 'https://example.com');
    });

    test('can match local variant', () {
      final VpnProfile profile = VpnProfile.local(
        id: 'p-2',
        name: 'Local',
        sortOrder: 0,
        createdAt: now,
      );

      final result = switch (profile) {
        RemoteVpnProfile() => 'remote',
        LocalVpnProfile(:final name) => name,
      };

      expect(result, 'Local');
    });
  });
}
