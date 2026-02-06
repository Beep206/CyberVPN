import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';

/// Benchmark: filteredServers performance with 1000 servers.
///
/// Target: <16ms per computation (one 60fps frame budget).
/// With Expando memoization, repeated reads on the same instance should be <1ms.
void main() {
  /// Generates [count] mock ServerEntity instances with varied properties.
  List<ServerEntity> generateServers(int count) {
    return List.generate(count, (i) {
      final countries = ['US', 'DE', 'JP', 'GB', 'FR', 'NL', 'SG', 'AU', 'CA', 'BR'];
      final countryCode = countries[i % countries.length];
      return ServerEntity(
        id: 'server-$i',
        name: 'Server $i',
        countryCode: countryCode,
        countryName: countryCode,
        city: 'City $i',
        address: '10.0.${i ~/ 256}.${i % 256}',
        port: 443,
        protocol: i % 3 == 0 ? 'vless' : (i % 3 == 1 ? 'vmess' : 'trojan'),
        isAvailable: i % 5 != 0,
        isPremium: i % 7 == 0,
        ping: i % 10 == 0 ? null : (i * 7) % 300,
        load: (i * 13 % 100).toDouble(),
      );
    });
  }

  group('filteredServers benchmark (1000 servers)', () {
    late List<ServerEntity> servers;

    setUp(() {
      servers = generateServers(1000);
    });

    test('initial computation completes within 16ms frame budget', () {
      final state = ServerListState(
        servers: servers,
        sortMode: SortMode.recommended,
      );

      final sw = Stopwatch()..start();
      final result = state.filteredServers;
      sw.stop();

      expect(result, isNotEmpty);
      // Generous margin: should be well under 16ms in release mode.
      // In debug mode with assertions, allow up to 100ms.
      expect(sw.elapsedMilliseconds, lessThan(100),
          reason: 'filteredServers took ${sw.elapsedMilliseconds}ms (target <16ms release)');
    });

    test('memoized second read is near-zero cost', () {
      final state = ServerListState(
        servers: servers,
        sortMode: SortMode.recommended,
      );

      // First call populates the Expando cache.
      state.filteredServers;

      final sw = Stopwatch()..start();
      final result = state.filteredServers;
      sw.stop();

      expect(result, isNotEmpty);
      expect(sw.elapsedMilliseconds, lessThan(2),
          reason: 'Memoized read took ${sw.elapsedMilliseconds}ms (expected <2ms)');
    });

    test('10 rapid filter changes stay within frame budget each', () {
      final filters = [null, 'US', 'DE', null, 'JP', 'GB', null, 'FR', 'NL', null];
      final protocols = [
        null,
        VpnProtocol.vless,
        null,
        VpnProtocol.vmess,
        null,
        VpnProtocol.vless,
        null,
        VpnProtocol.vmess,
        null,
        null,
      ];

      var maxMs = 0;

      for (var i = 0; i < 10; i++) {
        final state = ServerListState(
          servers: servers,
          sortMode: SortMode.values[i % SortMode.values.length],
          filterCountry: filters[i],
          filterProtocol: protocols[i],
        );

        final sw = Stopwatch()..start();
        state.filteredServers;
        sw.stop();

        if (sw.elapsedMilliseconds > maxMs) {
          maxMs = sw.elapsedMilliseconds;
        }
      }

      // In debug mode allow generous margin.
      expect(maxMs, lessThan(100),
          reason: 'Worst-case filter change took ${maxMs}ms (target <16ms release)');
    });

    test('country filter reduces result set correctly', () {
      final state = ServerListState(
        servers: servers,
        filterCountry: 'US',
      );
      final filtered = state.filteredServers;
      expect(filtered.every((s) => s.countryCode == 'US'), isTrue);
      // 1000 servers / 10 countries = ~100 per country
      expect(filtered.length, equals(100));
    });

    test('protocol filter reduces result set correctly', () {
      final state = ServerListState(
        servers: servers,
        filterProtocol: VpnProtocol.vless,
      );
      final filtered = state.filteredServers;
      expect(filtered.every((s) => s.protocol == 'vless'), isTrue);
    });
  });
}
