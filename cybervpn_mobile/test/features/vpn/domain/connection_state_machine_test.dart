import 'dart:async';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/connect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/disconnect_vpn.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../helpers/mock_factories.dart';
import '../../helpers/mock_repositories.dart';

void main() {
  late MockVpnRepository mockRepository;
  late ConnectVpnUseCase connectUseCase;
  late DisconnectVpnUseCase disconnectUseCase;

  setUpAll(() {
    registerFallbackValue(createMockVpnConfig());
  });

  setUp(() {
    mockRepository = MockVpnRepository();
    connectUseCase = ConnectVpnUseCase(mockRepository);
    disconnectUseCase = DisconnectVpnUseCase(mockRepository);
  });

  // ---------------------------------------------------------------------------
  // ConnectionStateEntity tests
  // ---------------------------------------------------------------------------

  group('ConnectionStateEntity', () {
    test('default state is disconnected', () {
      const state = ConnectionStateEntity();

      expect(state.status, VpnConnectionStatus.disconnected);
      expect(state.connectedServerId, isNull);
      expect(state.connectedAt, isNull);
      expect(state.errorMessage, isNull);
      expect(state.downloadSpeed, 0);
      expect(state.uploadSpeed, 0);
      expect(state.totalDownload, 0);
      expect(state.totalUpload, 0);
    });

    test('creates connecting state', () {
      final state = createMockConnectionState(
        status: VpnConnectionStatus.connecting,
      );

      expect(state.status, VpnConnectionStatus.connecting);
    });

    test('creates connected state with server info', () {
      final connectedAt = DateTime(2026, 1, 31, 12, 0);
      final state = createMockConnectionState(
        status: VpnConnectionStatus.connected,
        connectedServerId: 'server-001',
        connectedAt: connectedAt,
        downloadSpeed: 5000,
        uploadSpeed: 2000,
      );

      expect(state.status, VpnConnectionStatus.connected);
      expect(state.connectedServerId, 'server-001');
      expect(state.connectedAt, connectedAt);
      expect(state.downloadSpeed, 5000);
      expect(state.uploadSpeed, 2000);
    });

    test('creates disconnecting state', () {
      final state = createMockConnectionState(
        status: VpnConnectionStatus.disconnecting,
      );

      expect(state.status, VpnConnectionStatus.disconnecting);
    });

    test('creates error state with message', () {
      final state = createMockConnectionState(
        status: VpnConnectionStatus.error,
        errorMessage: 'Connection timed out',
      );

      expect(state.status, VpnConnectionStatus.error);
      expect(state.errorMessage, 'Connection timed out');
    });

    test('equality: two identical states are equal', () {
      final state1 = createMockConnectionState(
        status: VpnConnectionStatus.disconnected,
      );
      final state2 = createMockConnectionState(
        status: VpnConnectionStatus.disconnected,
      );

      expect(state1, equals(state2));
    });

    test('equality: different statuses are not equal', () {
      final state1 = createMockConnectionState(
        status: VpnConnectionStatus.disconnected,
      );
      final state2 = createMockConnectionState(
        status: VpnConnectionStatus.connected,
      );

      expect(state1, isNot(equals(state2)));
    });
  });

  // ---------------------------------------------------------------------------
  // VpnConnectionStatus enum tests
  // ---------------------------------------------------------------------------

  group('VpnConnectionStatus', () {
    test('contains all expected values', () {
      expect(VpnConnectionStatus.values, hasLength(5));
      expect(
        VpnConnectionStatus.values,
        containsAll([
          VpnConnectionStatus.disconnected,
          VpnConnectionStatus.connecting,
          VpnConnectionStatus.connected,
          VpnConnectionStatus.disconnecting,
          VpnConnectionStatus.error,
        ]),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // State transitions via use cases (Disconnected -> Connecting -> Connected)
  // ---------------------------------------------------------------------------

  group('ConnectVpnUseCase - state transitions', () {
    test('calls repository.connect with the given config', () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      await connectUseCase.call(config);

      verify(() => mockRepository.connect(config)).called(1);
    });

    test('connects with VLESS protocol config', () async {
      final config = createMockVpnConfig(protocol: VpnProtocol.vless);
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      await connectUseCase.call(config);

      verify(() => mockRepository.connect(config)).called(1);
    });

    test('connects with VMess protocol config', () async {
      final config = createMockVpnConfig(
        id: 'vmess-001',
        name: 'VMess Server',
        protocol: VpnProtocol.vmess,
      );
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      await connectUseCase.call(config);

      verify(() => mockRepository.connect(config)).called(1);
    });

    test('connects with Trojan protocol config', () async {
      final config = createMockVpnConfig(
        id: 'trojan-001',
        name: 'Trojan Server',
        protocol: VpnProtocol.trojan,
      );
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      await connectUseCase.call(config);

      verify(() => mockRepository.connect(config)).called(1);
    });

    test('connects with Shadowsocks protocol config', () async {
      final config = createMockVpnConfig(
        id: 'ss-001',
        name: 'SS Server',
        protocol: VpnProtocol.shadowsocks,
      );
      when(() => mockRepository.connect(any())).thenAnswer((_) async => const Success<void>(null));

      await connectUseCase.call(config);

      verify(() => mockRepository.connect(config)).called(1);
    });

    test('propagates repository error on connection failure', () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.connect(any()))
          .thenThrow(Exception('Connection refused'));

      expect(
        () => connectUseCase.call(config),
        throwsA(isA<Exception>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Disconnect transitions (Connected -> Disconnecting -> Disconnected)
  // ---------------------------------------------------------------------------

  group('DisconnectVpnUseCase - state transitions', () {
    test('calls repository.disconnect', () async {
      when(() => mockRepository.disconnect()).thenAnswer((_) async => const Success<void>(null));

      await disconnectUseCase.call();

      verify(() => mockRepository.disconnect()).called(1);
    });

    test('propagates repository error on disconnect failure', () async {
      when(() => mockRepository.disconnect())
          .thenThrow(Exception('Disconnect failed'));

      expect(
        () => disconnectUseCase.call(),
        throwsA(isA<Exception>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Connection state stream
  // ---------------------------------------------------------------------------

  group('VpnRepository - connectionStateStream', () {
    test('emits disconnected -> connecting -> connected transition', () async {
      final stateController = StreamController<ConnectionStateEntity>();

      when(() => mockRepository.connectionStateStream)
          .thenAnswer((_) => stateController.stream);

      final states = <ConnectionStateEntity>[];
      final subscription =
          mockRepository.connectionStateStream.listen(states.add);

      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.disconnected,
      ));
      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connecting,
      ));
      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connected,
        connectedServerId: 'server-001',
      ));

      await Future<void>.delayed(Duration.zero);
      await subscription.cancel();
      await stateController.close();

      expect(states, hasLength(3));
      expect(states[0].status, VpnConnectionStatus.disconnected);
      expect(states[1].status, VpnConnectionStatus.connecting);
      expect(states[2].status, VpnConnectionStatus.connected);
      expect(states[2].connectedServerId, 'server-001');
    });

    test(
        'emits connected -> disconnecting -> disconnected transition',
        () async {
      final stateController = StreamController<ConnectionStateEntity>();

      when(() => mockRepository.connectionStateStream)
          .thenAnswer((_) => stateController.stream);

      final states = <ConnectionStateEntity>[];
      final subscription =
          mockRepository.connectionStateStream.listen(states.add);

      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connected,
      ));
      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.disconnecting,
      ));
      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.disconnected,
      ));

      await Future<void>.delayed(Duration.zero);
      await subscription.cancel();
      await stateController.close();

      expect(states, hasLength(3));
      expect(states[0].status, VpnConnectionStatus.connected);
      expect(states[1].status, VpnConnectionStatus.disconnecting);
      expect(states[2].status, VpnConnectionStatus.disconnected);
    });

    test('emits error state on connection failure', () async {
      final stateController = StreamController<ConnectionStateEntity>();

      when(() => mockRepository.connectionStateStream)
          .thenAnswer((_) => stateController.stream);

      final states = <ConnectionStateEntity>[];
      final subscription =
          mockRepository.connectionStateStream.listen(states.add);

      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connecting,
      ));
      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.error,
        errorMessage: 'Server unreachable',
      ));

      await Future<void>.delayed(Duration.zero);
      await subscription.cancel();
      await stateController.close();

      expect(states, hasLength(2));
      expect(states[0].status, VpnConnectionStatus.connecting);
      expect(states[1].status, VpnConnectionStatus.error);
      expect(states[1].errorMessage, 'Server unreachable');
    });

    test('emits unexpected disconnect (connected -> disconnected)', () async {
      final stateController = StreamController<ConnectionStateEntity>();

      when(() => mockRepository.connectionStateStream)
          .thenAnswer((_) => stateController.stream);

      final states = <ConnectionStateEntity>[];
      final subscription =
          mockRepository.connectionStateStream.listen(states.add);

      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connected,
        connectedServerId: 'server-001',
      ));
      stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.error,
        errorMessage: 'Connection lost unexpectedly',
      ));

      await Future<void>.delayed(Duration.zero);
      await subscription.cancel();
      await stateController.close();

      expect(states, hasLength(2));
      expect(states[0].status, VpnConnectionStatus.connected);
      expect(states[1].status, VpnConnectionStatus.error);
      expect(states[1].errorMessage, 'Connection lost unexpectedly');
    });
  });

  // ---------------------------------------------------------------------------
  // Connection stats stream
  // ---------------------------------------------------------------------------

  group('VpnRepository - connectionStatsStream', () {
    test('emits connection statistics', () async {
      final statsController = StreamController<ConnectionStatsEntity>();

      when(() => mockRepository.connectionStatsStream)
          .thenAnswer((_) => statsController.stream);

      final stats = <ConnectionStatsEntity>[];
      final subscription =
          mockRepository.connectionStatsStream.listen(stats.add);

      statsController.add(createMockConnectionStats(
        downloadSpeed: 1024000,
        uploadSpeed: 512000,
        totalDownload: 10485760,
        totalUpload: 5242880,
        connectionDuration: const Duration(minutes: 5),
        serverName: 'US East 1',
        protocol: 'vless',
      ));

      await Future<void>.delayed(Duration.zero);
      await subscription.cancel();
      await statsController.close();

      expect(stats, hasLength(1));
      expect(stats[0].downloadSpeed, 1024000);
      expect(stats[0].uploadSpeed, 512000);
      expect(stats[0].serverName, 'US East 1');
      expect(stats[0].protocol, 'vless');
    });

    test('default stats are zero', () {
      const stats = ConnectionStatsEntity();

      expect(stats.downloadSpeed, 0);
      expect(stats.uploadSpeed, 0);
      expect(stats.totalDownload, 0);
      expect(stats.totalUpload, 0);
      expect(stats.connectionDuration, Duration.zero);
      expect(stats.serverName, isNull);
      expect(stats.protocol, isNull);
      expect(stats.ipAddress, isNull);
    });
  });

  // ---------------------------------------------------------------------------
  // VpnRepository - isConnected
  // ---------------------------------------------------------------------------

  group('VpnRepository - isConnected', () {
    test('returns true when connected', () async {
      when(() => mockRepository.isConnected)
          .thenAnswer((_) async => const Success(true));

      final result = await mockRepository.isConnected;

      expect(result, isA<Success<bool>>());
      expect((result as Success<bool>).data, isTrue);
    });

    test('returns false when disconnected', () async {
      when(() => mockRepository.isConnected)
          .thenAnswer((_) async => const Success(false));

      final result = await mockRepository.isConnected;

      expect(result, isA<Success<bool>>());
      expect((result as Success<bool>).data, isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // VpnRepository - config management
  // ---------------------------------------------------------------------------

  group('VpnRepository - config persistence', () {
    test('saveConfig and getLastConfig round-trip', () async {
      final config = createMockVpnConfig();
      when(() => mockRepository.saveConfig(any())).thenAnswer((_) async => const Success<void>(null));
      when(() => mockRepository.getLastConfig())
          .thenAnswer((_) async => Success(config));

      await mockRepository.saveConfig(config);
      final result = await mockRepository.getLastConfig();

      expect(result, isA<Success<VpnConfigEntity?>>());
      final retrieved = (result as Success<VpnConfigEntity?>).data;
      expect(retrieved, isNotNull);
      expect(retrieved!.id, config.id);
      expect(retrieved.name, config.name);
      expect(retrieved.protocol, config.protocol);
    });

    test('getLastConfig returns null when no config saved', () async {
      when(() => mockRepository.getLastConfig())
          .thenAnswer((_) async => const Success<VpnConfigEntity?>(null));

      final result = await mockRepository.getLastConfig();

      expect(result, isA<Success<VpnConfigEntity?>>());
      expect((result as Success<VpnConfigEntity?>).data, isNull);
    });

    test('getSavedConfigs returns list of configs', () async {
      final configs = [
        createMockVpnConfig(id: 'config-1', name: 'Server 1'),
        createMockVpnConfig(id: 'config-2', name: 'Server 2'),
        createMockVpnConfig(id: 'config-3', name: 'Server 3'),
      ];
      when(() => mockRepository.getSavedConfigs())
          .thenAnswer((_) async => Success(configs));

      final result = await mockRepository.getSavedConfigs();

      expect(result, isA<Success<List<VpnConfigEntity>>>());
      final data = (result as Success<List<VpnConfigEntity>>).data;
      expect(data, hasLength(3));
      expect(data[0].id, 'config-1');
      expect(data[2].id, 'config-3');
    });

    test('getSavedConfigs returns empty list when none saved', () async {
      when(() => mockRepository.getSavedConfigs())
          .thenAnswer((_) async => const Success(<VpnConfigEntity>[]));

      final result = await mockRepository.getSavedConfigs();

      expect(result, isA<Success<List<VpnConfigEntity>>>());
      expect((result as Success<List<VpnConfigEntity>>).data, isEmpty);
    });

    test('deleteConfig removes config by id', () async {
      when(() => mockRepository.deleteConfig(any()))
          .thenAnswer((_) async => const Success<void>(null));

      await mockRepository.deleteConfig('config-to-delete');

      verify(() => mockRepository.deleteConfig('config-to-delete')).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // VpnConfigEntity tests
  // ---------------------------------------------------------------------------

  group('VpnConfigEntity', () {
    test('creates entity with all required fields', () {
      final config = createMockVpnConfig();

      expect(config.id, 'vpn-config-001');
      expect(config.name, 'US East VLESS');
      expect(config.serverAddress, '203.0.113.1');
      expect(config.port, 443);
      expect(config.protocol, VpnProtocol.vless);
      expect(config.configData, isNotEmpty);
      expect(config.isFavorite, isFalse);
    });

    test('creates entity with optional remark', () {
      final config = createMockVpnConfig(remark: 'Test remark');

      expect(config.remark, 'Test remark');
    });

    test('creates entity with favorite flag', () {
      final config = createMockVpnConfig(isFavorite: true);

      expect(config.isFavorite, isTrue);
    });

    test('equality: identical configs are equal', () {
      final config1 = createMockVpnConfig();
      final config2 = createMockVpnConfig();

      expect(config1, equals(config2));
    });

    test('equality: different ids make configs unequal', () {
      final config1 = createMockVpnConfig(id: 'config-a');
      final config2 = createMockVpnConfig(id: 'config-b');

      expect(config1, isNot(equals(config2)));
    });
  });

  // ---------------------------------------------------------------------------
  // VpnProtocol enum tests
  // ---------------------------------------------------------------------------

  group('VpnProtocol', () {
    test('contains all supported protocols', () {
      expect(VpnProtocol.values, hasLength(4));
      expect(
        VpnProtocol.values,
        containsAll([
          VpnProtocol.vless,
          VpnProtocol.vmess,
          VpnProtocol.trojan,
          VpnProtocol.shadowsocks,
        ]),
      );
    });

    test('name returns correct string', () {
      expect(VpnProtocol.vless.name, 'vless');
      expect(VpnProtocol.vmess.name, 'vmess');
      expect(VpnProtocol.trojan.name, 'trojan');
      expect(VpnProtocol.shadowsocks.name, 'shadowsocks');
    });
  });
}
