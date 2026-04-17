import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';

void main() {
  group('ExcludedRouteEntry', () {
    test('parses IPv4 address', () {
      final entry = ExcludedRouteEntry.parse('192.168.0.1');

      expect(entry.normalizedValue, '192.168.0.1');
      expect(entry.targetType, ExcludedRouteTargetType.ipv4Address);
      expect(entry.isCidr, isFalse);
      expect(entry.isIpv6, isFalse);
    });

    test('parses IPv4 CIDR', () {
      final entry = ExcludedRouteEntry.parse('192.168.0.0/16');

      expect(entry.targetType, ExcludedRouteTargetType.ipv4Cidr);
      expect(entry.isCidr, isTrue);
    });

    test('parses IPv6 address', () {
      final entry = ExcludedRouteEntry.parse('2001:db8::1');

      expect(entry.targetType, ExcludedRouteTargetType.ipv6Address);
      expect(entry.isIpv6, isTrue);
      expect(entry.isCidr, isFalse);
    });

    test('parses IPv6 CIDR', () {
      final entry = ExcludedRouteEntry.parse('2001:db8::/32');

      expect(entry.targetType, ExcludedRouteTargetType.ipv6Cidr);
      expect(entry.isIpv6, isTrue);
      expect(entry.isCidr, isTrue);
    });

    test('falls back to unknown for invalid values', () {
      final entry = ExcludedRouteEntry.parse('not-a-route');

      expect(entry.targetType, ExcludedRouteTargetType.unknown);
    });

    test('round-trips through storage json', () {
      final entry = ExcludedRouteEntry.parse('10.0.0.0/8');

      final restored = ExcludedRouteEntry.fromStorageJson(
        entry.toStorageJson(),
      );

      expect(restored, entry);
    });
  });
}
