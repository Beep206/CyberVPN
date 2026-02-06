import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

import 'test_app.dart';
import 'test_utils.dart';
import 'mock_factories.dart';
import 'mock_repositories.dart';
import 'fakes/fake_secure_storage.dart';
import 'fakes/fake_local_storage.dart';
import 'fakes/fake_api_client.dart';
import 'fixture_loader.dart';

void main() {
  group('TestApp widget wrapper', () {
    testWidgets('renders child widget inside MaterialApp', (tester) async {
      await tester.pumpTestApp(
        const Text('Hello Test'),
      );

      expect(find.text('Hello Test'), findsOneWidget);
    });

    testWidgets('supports dark theme mode', (tester) async {
      await tester.pumpTestApp(
        const Text('Dark Theme'),
        themeMode: ThemeMode.dark,
      );

      expect(find.text('Dark Theme'), findsOneWidget);
    });

    testWidgets('supports RTL text direction', (tester) async {
      await tester.pumpTestApp(
        const Text('RTL Text'),
        textDirection: TextDirection.rtl,
      );

      expect(find.text('RTL Text'), findsOneWidget);
    });
  });

  group('Mock factories', () {
    test('createMockUser returns valid UserEntity', () {
      final user = createMockUser();

      expect(user, isA<UserEntity>());
      expect(user.id, 'user-001');
      expect(user.email, 'test@example.com');
      expect(user.username, 'testuser');
      expect(user.isEmailVerified, isTrue);
      expect(user.isPremium, isFalse);
    });

    test('createMockUser accepts overrides', () {
      final user = createMockUser(
        id: 'custom-id',
        email: 'custom@test.com',
        isPremium: true,
      );

      expect(user.id, 'custom-id');
      expect(user.email, 'custom@test.com');
      expect(user.isPremium, isTrue);
    });

    test('createMockPremiumUser returns premium user', () {
      final user = createMockPremiumUser();

      expect(user.isPremium, isTrue);
      expect(user.isEmailVerified, isTrue);
    });

    test('createMockServer returns valid ServerEntity', () {
      final server = createMockServer();

      expect(server, isA<ServerEntity>());
      expect(server.id, 'server-001');
      expect(server.isAvailable, isTrue);
      expect(server.ping, 45);
    });

    test('createMockServerList returns correct count', () {
      final servers = createMockServerList(count: 3);

      expect(servers, hasLength(3));
      expect(servers.every((s) => s is ServerEntity), isTrue);
    });

    test('createMockPlan returns valid PlanEntity', () {
      final plan = createMockPlan();

      expect(plan, isA<PlanEntity>());
      expect(plan.price, 9.99);
      expect(plan.features, isNotEmpty);
    });

    test('createMockPlanList returns all plan types', () {
      final plans = createMockPlanList();

      expect(plans.length, greaterThanOrEqualTo(4));
      expect(plans.any((p) => p.isTrial), isTrue);
      expect(plans.any((p) => p.isPopular), isTrue);
    });

    test('createMockSubscription returns valid SubscriptionEntity', () {
      final sub = createMockSubscription();

      expect(sub, isA<SubscriptionEntity>());
      expect(sub.status, SubscriptionStatus.active);
    });

    test('createMockExpiredSubscription returns expired status', () {
      final sub = createMockExpiredSubscription();

      expect(sub.status, SubscriptionStatus.expired);
    });

    test('createMockImportedConfig returns valid ImportedConfig', () {
      final config = createMockImportedConfig();

      expect(config, isA<ImportedConfig>());
      expect(config.protocol, 'vless');
      expect(config.source, ImportSource.clipboard);
    });

    test('createMockVpnConfig returns valid VpnConfigEntity', () {
      final config = createMockVpnConfig();

      expect(config, isA<VpnConfigEntity>());
      expect(config.protocol, VpnProtocol.vless);
    });

    test('createMockConnectionState returns valid entity', () {
      final state = createMockConnectionState();

      expect(state, isA<ConnectionStateEntity>());
      expect(state.status, VpnConnectionStatus.disconnected);
    });

    test('createMockConnectionStats returns valid entity', () {
      final stats = createMockConnectionStats();

      expect(stats, isA<ConnectionStatsEntity>());
      expect(stats.downloadSpeed, greaterThan(0));
    });
  });

  group('Mock repositories', () {
    test('MockAuthRepository can be instantiated', () {
      final mock = MockAuthRepository();
      expect(mock, isA<MockAuthRepository>());
    });

    test('MockServerRepository can be stubbed', () {
      final mock = MockServerRepository();
      when(() => mock.getServers()).thenAnswer(
        (_) async => Success(createMockServerList()),
      );

      expect(mock.getServers(), completes);
    });

    test('MockSubscriptionRepository can be stubbed', () {
      final mock = MockSubscriptionRepository();
      when(() => mock.getPlans()).thenAnswer(
        (_) async => Success(createMockPlanList()),
      );

      expect(mock.getPlans(), completes);
    });

    test('MockVpnRepository can be instantiated', () {
      final mock = MockVpnRepository();
      expect(mock, isA<MockVpnRepository>());
    });

    test('MockConfigImportRepository can be instantiated', () {
      final mock = MockConfigImportRepository();
      expect(mock, isA<MockConfigImportRepository>());
    });
  });

  group('FakeSecureStorage', () {
    late FakeSecureStorage storage;

    setUp(() {
      storage = FakeSecureStorage();
    });

    test('write and read', () async {
      await storage.write(key: 'token', value: 'abc123');
      final result = await storage.read(key: 'token');

      expect(result, 'abc123');
    });

    test('read returns null for missing key', () async {
      final result = await storage.read(key: 'missing');
      expect(result, isNull);
    });

    test('delete removes key', () async {
      await storage.write(key: 'token', value: 'abc123');
      await storage.delete(key: 'token');

      expect(await storage.read(key: 'token'), isNull);
    });

    test('deleteAll clears storage', () async {
      await storage.write(key: 'a', value: '1');
      await storage.write(key: 'b', value: '2');
      await storage.deleteAll();

      expect(storage.store, isEmpty);
    });

    test('containsKey works correctly', () async {
      await storage.write(key: 'exists', value: 'yes');

      expect(await storage.containsKey(key: 'exists'), isTrue);
      expect(await storage.containsKey(key: 'nope'), isFalse);
    });
  });

  group('FakeLocalStorage', () {
    late FakeLocalStorage storage;

    setUp(() {
      storage = FakeLocalStorage();
    });

    test('setString and getString', () async {
      await storage.setString('name', 'test');
      expect(await storage.getString('name'), 'test');
    });

    test('setBool and getBool', () async {
      await storage.setBool('flag', true);
      expect(await storage.getBool('flag'), isTrue);
    });

    test('setInt and getInt', () async {
      await storage.setInt('count', 42);
      expect(await storage.getInt('count'), 42);
    });

    test('remove deletes key', () async {
      await storage.setString('key', 'value');
      await storage.remove('key');
      expect(await storage.getString('key'), isNull);
    });

    test('clear removes all', () async {
      await storage.setString('a', '1');
      await storage.setInt('b', 2);
      await storage.clear();
      expect(storage.store, isEmpty);
    });
  });

  group('FakeApiClient', () {
    late FakeApiClient api;

    setUp(() {
      api = FakeApiClient();
    });

    test('returns configured GET response', () async {
      api.setGetResponse('/users/me', {'id': 'user-001'});

      final response = await api.get<Map<String, dynamic>>('/users/me');
      expect(response.data?['id'], 'user-001');
      expect(response.statusCode, 200);
    });

    test('returns configured POST response', () async {
      api.setPostResponse('/auth/login', {'token': 'jwt-token'});

      final response = await api.post<Map<String, dynamic>>('/auth/login');
      expect(response.data?['token'], 'jwt-token');
    });

    test('throws error for unconfigured path', () {
      expect(
        () => api.get('/unknown'),
        throwsA(isA<StateError>()),
      );
    });

    test('throws configured error', () {
      api.setGetError('/fail', Exception('Network error'));

      expect(
        () => api.get('/fail'),
        throwsA(isA<Exception>()),
      );
    });

    test('reset clears all responses', () {
      api.setGetResponse('/test', 'data');
      api.reset();

      expect(
        () => api.get('/test'),
        throwsA(isA<StateError>()),
      );
    });
  });

  group('Fixture loader', () {
    test('loads user fixture', () async {
      final data = await loadFixture('user_fixture.json');
      expect(data, isA<List<dynamic>>());
      expect((data as List<dynamic>).length, greaterThanOrEqualTo(5));
      expect(data.first['id'], isNotEmpty);
      expect(data.first['email'], isNotEmpty);
    });

    test('loads servers fixture', () async {
      final data = await loadFixture('servers_fixture.json');
      expect(data, isA<List<dynamic>>());
      expect((data as List<dynamic>).length, greaterThanOrEqualTo(20));
    });

    test('loads plans fixture', () async {
      final data = await loadFixture('plans_fixture.json');
      expect(data, isA<List<dynamic>>());
      expect((data as List<dynamic>).length, greaterThanOrEqualTo(4));
    });

    test('loads vpn config fixture', () async {
      final data = await loadFixture('vpn_config_fixture.json');
      expect(data, isA<List<dynamic>>());
      expect((data as List<dynamic>), isNotEmpty);
    });

    test('loads subscriptions fixture', () async {
      final data = await loadFixture('subscriptions_fixture.json');
      expect(data, isA<List<dynamic>>());
      expect((data as List<dynamic>).length, greaterThanOrEqualTo(5));
    });

    test('subscriptions fixture contains all statuses', () async {
      final data =
          await loadFixture('subscriptions_fixture.json') as List<dynamic>;
      final statuses = data.map((s) => s['status'] as String).toSet();

      expect(statuses, contains('active'));
      expect(statuses, contains('expired'));
      expect(statuses, contains('cancelled'));
      expect(statuses, contains('trial'));
      expect(statuses, contains('pending'));
    });

    test('servers fixture contains offline servers', () async {
      final data =
          await loadFixture('servers_fixture.json') as List<dynamic>;
      final unavailable = data.where((s) => s['isAvailable'] == false);
      expect(unavailable, isNotEmpty);
    });
  });

  group('Test utils', () {
    testWidgets('findByText locates text widget', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Text('Find me')),
      );

      expect(findByText('Find me'), findsOneWidget);
    });

    testWidgets('testKey creates unique key', (tester) async {
      final key = testKey('my_widget');
      await tester.pumpWidget(
        MaterialApp(
          home: Container(key: key),
        ),
      );

      expect(findByKey(key), findsOneWidget);
    });
  });
}
