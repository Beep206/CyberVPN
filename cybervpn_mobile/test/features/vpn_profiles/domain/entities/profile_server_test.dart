import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final now = DateTime(2026, 2, 15, 12, 0, 0);

  group('ProfileServer', () {
    late ProfileServer server;

    setUp(() {
      server = ProfileServer(
        id: 'srv-1',
        profileId: 'p-1',
        name: 'US East',
        serverAddress: '203.0.113.1',
        port: 443,
        protocol: VpnProtocol.vless,
        configData: '{"uuid":"test-uuid"}',
        sortOrder: 0,
        createdAt: now,
      );
    });

    test('creates with all required fields', () {
      expect(server.id, 'srv-1');
      expect(server.profileId, 'p-1');
      expect(server.name, 'US East');
      expect(server.serverAddress, '203.0.113.1');
      expect(server.port, 443);
      expect(server.protocol, VpnProtocol.vless);
      expect(server.configData, '{"uuid":"test-uuid"}');
      expect(server.sortOrder, 0);
      expect(server.createdAt, now);
    });

    test('defaults are applied correctly', () {
      expect(server.isFavorite, false);
    });

    test('optional fields default to null', () {
      expect(server.remark, isNull);
      expect(server.latencyMs, isNull);
    });

    test('creates with all optional fields', () {
      final full = ProfileServer(
        id: 'srv-full',
        profileId: 'p-1',
        name: 'Frankfurt DE',
        serverAddress: '10.0.0.1',
        port: 8443,
        protocol: VpnProtocol.vmess,
        configData: '{"id":"vmess-uuid"}',
        remark: 'Fast server',
        isFavorite: true,
        sortOrder: 1,
        latencyMs: 45,
        createdAt: now,
      );

      expect(full.remark, 'Fast server');
      expect(full.isFavorite, true);
      expect(full.latencyMs, 45);
    });

    test('copyWith preserves unchanged fields', () {
      final updated = server.copyWith(name: 'US West');

      expect(updated.name, 'US West');
      expect(updated.id, server.id);
      expect(updated.profileId, server.profileId);
      expect(updated.serverAddress, server.serverAddress);
      expect(updated.port, server.port);
      expect(updated.protocol, server.protocol);
      expect(updated.configData, server.configData);
      expect(updated.remark, server.remark);
      expect(updated.isFavorite, server.isFavorite);
      expect(updated.sortOrder, server.sortOrder);
      expect(updated.latencyMs, server.latencyMs);
      expect(updated.createdAt, server.createdAt);
    });

    test('copyWith updates multiple fields', () {
      final updated = server.copyWith(
        isFavorite: true,
        latencyMs: 30,
        remark: 'Pinged',
      );

      expect(updated.isFavorite, true);
      expect(updated.latencyMs, 30);
      expect(updated.remark, 'Pinged');
      expect(updated.id, server.id);
    });

    test('equality for identical servers', () {
      final server2 = ProfileServer(
        id: 'srv-1',
        profileId: 'p-1',
        name: 'US East',
        serverAddress: '203.0.113.1',
        port: 443,
        protocol: VpnProtocol.vless,
        configData: '{"uuid":"test-uuid"}',
        sortOrder: 0,
        createdAt: now,
      );

      expect(server, equals(server2));
      expect(server.hashCode, equals(server2.hashCode));
    });

    test('inequality when id differs', () {
      final server2 = ProfileServer(
        id: 'srv-different',
        profileId: 'p-1',
        name: 'US East',
        serverAddress: '203.0.113.1',
        port: 443,
        protocol: VpnProtocol.vless,
        configData: '{"uuid":"test-uuid"}',
        sortOrder: 0,
        createdAt: now,
      );

      expect(server, isNot(equals(server2)));
    });

    test('inequality when protocol differs', () {
      final server2 = server.copyWith(protocol: VpnProtocol.trojan);

      expect(server, isNot(equals(server2)));
    });

    test('works with all VpnProtocol values', () {
      for (final protocol in VpnProtocol.values) {
        final s = ProfileServer(
          id: 'srv-${protocol.name}',
          profileId: 'p-1',
          name: '${protocol.name} server',
          serverAddress: '10.0.0.1',
          port: 443,
          protocol: protocol,
          configData: '{}',
          sortOrder: 0,
          createdAt: now,
        );
        expect(s.protocol, protocol);
      }
    });

    test('toString contains meaningful info', () {
      final str = server.toString();
      expect(str, contains('srv-1'));
    });
  });
}
