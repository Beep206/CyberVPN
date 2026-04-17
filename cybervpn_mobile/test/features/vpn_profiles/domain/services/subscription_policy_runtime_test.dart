import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/data/models/parsed_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/services/subscription_policy_runtime.dart';

void main() {
  const runtime = SubscriptionPolicyRuntime();

  group('SubscriptionPolicyRuntime', () {
    test('falls back to the app default user-agent', () {
      final policy = runtime.resolve(const AppSettings());

      expect(
        policy.effectiveUserAgent,
        SubscriptionPolicyRuntime.defaultUserAgent,
      );
    });

    test('uses a custom user-agent override when configured', () {
      final policy = runtime.resolve(
        const AppSettings(
          subscriptionUserAgentMode: SubscriptionUserAgentMode.custom,
          subscriptionUserAgentValue: 'CyberVPN-Test/8.0',
        ),
      );

      expect(policy.effectiveUserAgent, 'CyberVPN-Test/8.0');
    });

    test('sorts imported configs alphabetically when requested', () {
      final policy = runtime.resolve(
        const AppSettings(
          subscriptionSortMode: SubscriptionSortMode.alphabetical,
        ),
      );
      final configs = [
        ImportedConfig(
          id: '2',
          name: 'Zurich',
          rawUri: 'vless://2',
          protocol: 'vless',
          serverAddress: 'z.example.com',
          port: 443,
          source: ImportSource.subscriptionUrl,
          importedAt: DateTime(2026, 4, 17),
        ),
        ImportedConfig(
          id: '1',
          name: 'Amsterdam',
          rawUri: 'vless://1',
          protocol: 'vless',
          serverAddress: 'a.example.com',
          port: 443,
          source: ImportSource.subscriptionUrl,
          importedAt: DateTime(2026, 4, 17),
        ),
      ];

      final sorted = runtime.sortImportedConfigs(configs, policy);

      expect(sorted.map((config) => config.name), ['Amsterdam', 'Zurich']);
    });

    test('sorts parsed servers by cached latency in ping mode', () {
      const policy = SubscriptionPolicyState(sortMode: SubscriptionSortMode.ping);
      final servers = [
        const ParsedServer(
          name: 'Tokyo',
          rawUri: 'vless://tokyo',
          protocol: 'vless',
          serverAddress: 'tokyo.example.com',
          port: 443,
          configData: {'id': 'tokyo'},
        ),
        const ParsedServer(
          name: 'Berlin',
          rawUri: 'vless://berlin',
          protocol: 'vless',
          serverAddress: 'berlin.example.com',
          port: 443,
          configData: {'id': 'berlin'},
        ),
      ];
      final existingServers = [
        ProfileServer(
          id: 'tokyo-id',
          profileId: 'profile-1',
          name: 'Tokyo',
          serverAddress: 'tokyo.example.com',
          port: 443,
          protocol: VpnProtocol.vless,
          configData: '{}',
          sortOrder: 0,
          latencyMs: 140,
          createdAt: DateTime(2026, 4, 17),
        ),
        ProfileServer(
          id: 'berlin-id',
          profileId: 'profile-1',
          name: 'Berlin',
          serverAddress: 'berlin.example.com',
          port: 443,
          protocol: VpnProtocol.vless,
          configData: '{}',
          sortOrder: 1,
          latencyMs: 40,
          createdAt: DateTime(2026, 4, 17),
        ),
      ];

      final sorted = runtime.sortParsedServers(
        servers,
        policy,
        existingServers: existingServers,
      );

      expect(sorted.map((server) => server.name), ['Berlin', 'Tokyo']);
    });

    test('reorders existing servers by latency when ping sort is enabled', () {
      const policy = SubscriptionPolicyState(sortMode: SubscriptionSortMode.ping);
      final servers = [
        ProfileServer(
          id: '1',
          profileId: 'profile-1',
          name: 'Tokyo',
          serverAddress: 'tokyo.example.com',
          port: 443,
          protocol: VpnProtocol.vless,
          configData: '{}',
          sortOrder: 0,
          latencyMs: 140,
          createdAt: DateTime(2026, 4, 17),
        ),
        ProfileServer(
          id: '2',
          profileId: 'profile-1',
          name: 'Berlin',
          serverAddress: 'berlin.example.com',
          port: 443,
          protocol: VpnProtocol.vless,
          configData: '{}',
          sortOrder: 1,
          latencyMs: 40,
          createdAt: DateTime(2026, 4, 17),
        ),
      ];

      final sorted = runtime.sortExistingServers(servers, policy);

      expect(sorted.map((server) => server.name), ['Berlin', 'Tokyo']);
      expect(sorted.map((server) => server.sortOrder), [0, 1]);
    });

    test('prefers the lowest-latency server when connect strategy is set', () {
      const policy = SubscriptionPolicyState(
        connectStrategy: SubscriptionConnectStrategy.lowestDelay,
      );
      final selection = runtime.selectAutoConnectServer(
        policy: policy,
        availableServers: [
          _server(id: 'slow', name: 'Slow', ping: 180),
          _server(id: 'fast', name: 'Fast', ping: 35),
          _server(id: 'mid', name: 'Mid', ping: 90),
        ],
      );

      expect(selection, isNotNull);
      expect(selection!.server.id, 'fast');
      expect(
        selection.appliedStrategy,
        SubscriptionConnectStrategy.lowestDelay,
      );
      expect(selection.usedFallback, isFalse);
    });

    test('falls back to recommended server when last used is unavailable', () {
      const policy = SubscriptionPolicyState(
        connectStrategy: SubscriptionConnectStrategy.lastUsed,
      );
      final selection = runtime.selectAutoConnectServer(
        policy: policy,
        availableServers: const <ServerEntity>[],
        lastServer: _server(
          id: 'last',
          name: 'Last',
          ping: 120,
          isAvailable: false,
        ),
        recommendedServer: _server(id: 'recommended', name: 'Recommended'),
      );

      expect(selection, isNotNull);
      expect(selection!.server.id, 'recommended');
      expect(
        selection.appliedStrategy,
        SubscriptionConnectStrategy.lowestDelay,
      );
      expect(selection.usedFallback, isTrue);
    });

    test('uses deterministic random selection when seeded', () {
      final runtimeWithSeed = SubscriptionPolicyRuntime(random: math.Random(7));
      const policy = SubscriptionPolicyState(
        connectStrategy: SubscriptionConnectStrategy.random,
      );
      final servers = [
        _server(id: 'a', name: 'Alpha', ping: 10),
        _server(id: 'b', name: 'Bravo', ping: 20),
        _server(id: 'c', name: 'Charlie', ping: 30),
      ];
      final expectedIndex = math.Random(7).nextInt(servers.length);

      final selection = runtimeWithSeed.selectAutoConnectServer(
        policy: policy,
        availableServers: servers,
      );

      expect(selection, isNotNull);
      expect(selection!.server.id, servers[expectedIndex].id);
      expect(selection.appliedStrategy, SubscriptionConnectStrategy.random);
    });
  });
}

ServerEntity _server({
  required String id,
  required String name,
  int? ping,
  bool isAvailable = true,
  bool isPremium = false,
}) {
  return ServerEntity(
    id: id,
    name: name,
    countryCode: 'US',
    countryName: 'United States',
    city: 'New York',
    address: '$id.example.com',
    port: 443,
    protocol: 'vless',
    isAvailable: isAvailable,
    isPremium: isPremium,
    ping: ping,
  );
}
