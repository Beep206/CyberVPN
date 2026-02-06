import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ServerEntity JSON round-trip', () {
    test('round-trips all fields through toJson/fromJson', () {
      const original = ServerEntity(
        id: 'srv-1',
        name: 'US East',
        countryCode: 'US',
        countryName: 'United States',
        city: 'New York',
        address: '1.2.3.4',
        port: 443,
        protocol: 'vless',
        isAvailable: true,
        isPremium: true,
        isFavorite: true,
        ping: 42,
        load: 0.75,
      );

      final json = original.toJson();
      final restored = ServerEntity.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.name, original.name);
      expect(restored.countryCode, original.countryCode);
      expect(restored.countryName, original.countryName);
      expect(restored.city, original.city);
      expect(restored.address, original.address);
      expect(restored.port, original.port);
      expect(restored.protocol, original.protocol);
      expect(restored.isAvailable, original.isAvailable);
      expect(restored.isPremium, original.isPremium);
      expect(restored.isFavorite, original.isFavorite);
      expect(restored.ping, original.ping);
      expect(restored.load, original.load);
    });

    test('round-trips with default/null optional fields', () {
      const original = ServerEntity(
        id: 'srv-2',
        name: 'DE Frankfurt',
        countryCode: 'DE',
        countryName: 'Germany',
        city: 'Frankfurt',
        address: '5.6.7.8',
        port: 8443,
      );

      final json = original.toJson();
      final restored = ServerEntity.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.protocol, 'vless');
      expect(restored.isAvailable, true);
      expect(restored.isPremium, false);
      expect(restored.isFavorite, false);
      expect(restored.ping, isNull);
      expect(restored.load, isNull);
    });

    test('fromJson handles missing optional fields gracefully', () {
      final json = <String, dynamic>{
        'id': 'srv-3',
        'name': 'JP Tokyo',
        'countryCode': 'JP',
        'countryName': 'Japan',
        'city': 'Tokyo',
        'address': '10.0.0.1',
        'port': 443,
      };

      final entity = ServerEntity.fromJson(json);

      expect(entity.protocol, 'vless');
      expect(entity.isAvailable, true);
      expect(entity.isPremium, false);
      expect(entity.isFavorite, false);
      expect(entity.ping, isNull);
      expect(entity.load, isNull);
    });
  });
}
