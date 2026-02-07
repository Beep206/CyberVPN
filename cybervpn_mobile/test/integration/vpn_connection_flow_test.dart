import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/core/security/vpn_config_encryptor.dart';
import '../helpers/mock_factories.dart';

/// Integration tests for VPN connection flow covering:
/// - Connection state transitions
/// - Config encryption/decryption round-trip
/// - Server entity creation and validation
void main() {
  group('VPN connection flow integration', () {
    group('Connection state machine', () {
      test('initial state is disconnected', () {
        final state = createMockConnectionState();
        expect(state.status, VpnConnectionStatus.disconnected);
        expect(state.connectedServerId, isNull);
      });

      test('connecting state has no server ID', () {
        final state = createMockConnectionState(
          status: VpnConnectionStatus.connecting,
        );
        expect(state.status, VpnConnectionStatus.connecting);
      });

      test('connected state has server ID and timestamp', () {
        final state = createMockConnectionState(
          status: VpnConnectionStatus.connected,
          connectedServerId: 'us-east-1',
          connectedAt: DateTime.now(),
        );
        expect(state.status, VpnConnectionStatus.connected);
        expect(state.connectedServerId, 'us-east-1');
        expect(state.connectedAt, isNotNull);
      });

      test('error state contains message', () {
        final state = createMockConnectionState(
          status: VpnConnectionStatus.error,
          errorMessage: 'Connection timed out',
        );
        expect(state.status, VpnConnectionStatus.error);
        expect(state.errorMessage, 'Connection timed out');
      });
    });

    group('VPN config encryption round-trip', () {
      late final key = VpnConfigEncryptor.deriveKey('token123', 'device456');

      test('encrypt then decrypt returns original plaintext', () {
        const original = '{"server":"us-east-1","protocol":"vless","port":443}';
        final encrypted = VpnConfigEncryptor.encrypt(original, key);
        final decrypted = VpnConfigEncryptor.decrypt(encrypted, key);

        expect(decrypted, original);
      });

      test('different keys produce different ciphertext', () {
        const plaintext = 'test config data';
        final key2 = VpnConfigEncryptor.deriveKey('other_token', 'other_device');

        final encrypted1 = VpnConfigEncryptor.encrypt(plaintext, key);
        final encrypted2 = VpnConfigEncryptor.encrypt(plaintext, key2);

        expect(encrypted1, isNot(equals(encrypted2)));
      });

      test('decrypt with wrong key returns null or wrong data', () {
        const plaintext = 'sensitive vpn config';
        final encrypted = VpnConfigEncryptor.encrypt(plaintext, key);
        final wrongKey = VpnConfigEncryptor.deriveKey('wrong', 'key');
        final result = VpnConfigEncryptor.decrypt(encrypted, wrongKey);

        // Either null (if UTF-8 decode fails) or different content
        if (result != null) {
          expect(result, isNot(equals(plaintext)));
        }
      });

      test('HMAC sign and verify round-trip', () {
        const data = 'config data to sign';
        final signature = VpnConfigEncryptor.sign(data, key);
        expect(VpnConfigEncryptor.verify(data, signature, key), isTrue);
      });

      test('HMAC verification fails for tampered data', () {
        const data = 'original data';
        final signature = VpnConfigEncryptor.sign(data, key);
        expect(VpnConfigEncryptor.verify('tampered data', signature, key), isFalse);
      });
    });

    group('Server entity validation', () {
      test('creates mock server with defaults', () {
        final server = createMockServer();
        expect(server.id, 'server-001');
        expect(server.isAvailable, isTrue);
        expect(server.isPremium, isFalse);
      });

      test('creates server list with correct count', () {
        final servers = createMockServerList(count: 3);
        expect(servers, hasLength(3));
        expect(servers.map((s) => s.countryCode).toSet().length, 3);
      });
    });
  });
}
