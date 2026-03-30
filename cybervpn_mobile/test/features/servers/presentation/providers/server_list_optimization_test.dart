import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/profile_aware_server_list.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';

class _ProfileAwareStateNotifier extends Notifier<AsyncValue<ServerListState>> {
  _ProfileAwareStateNotifier(this._initialState);

  final ServerListState _initialState;

  @override
  AsyncValue<ServerListState> build() => AsyncData(_initialState);

  void setServerListState(ServerListState nextState) {
    state = AsyncData(nextState);
  }
}

ServerEntity _server({
  required String id,
  required String countryCode,
  required String countryName,
  required String name,
  required int ping,
}) {
  return ServerEntity(
    id: id,
    name: name,
    countryCode: countryCode,
    countryName: countryName,
    city: 'City $id',
    address: '$id.example.com',
    port: 443,
    ping: ping,
  );
}

void main() {
  group('server list optimization providers', () {
    test('serverByIdProvider only notifies for the selected server', () async {
      final selectedServer = _server(
        id: 'us-1',
        countryCode: 'US',
        countryName: 'United States',
        name: 'US 1',
        ping: 20,
      );
      final otherServer = _server(
        id: 'de-1',
        countryCode: 'DE',
        countryName: 'Germany',
        name: 'DE 1',
        ping: 80,
      );
      final initialState = ServerListState(
        servers: [selectedServer, otherServer],
        sortMode: SortMode.countryName,
      );
      final profileAwareStateProvider =
          NotifierProvider<
            _ProfileAwareStateNotifier,
            AsyncValue<ServerListState>
          >(() => _ProfileAwareStateNotifier(initialState));

      final container = ProviderContainer(
        overrides: [
          profileAwareServerListProvider.overrideWith(
            (ref) => ref.watch(profileAwareStateProvider),
          ),
          importedConfigsProvider.overrideWith((ref) => const []),
        ],
      );
      addTearDown(container.dispose);

      var notificationCount = 0;
      final sub = container.listen<ServerEntity?>(
        serverByIdProvider('us-1'),
        (previous, next) => notificationCount++,
      );
      addTearDown(sub.close);

      expect(container.read(serverByIdProvider('us-1')), selectedServer);

      container
          .read(profileAwareStateProvider.notifier)
          .setServerListState(
            initialState.copyWith(
              servers: [selectedServer, otherServer.copyWith(ping: 95)],
            ),
          );
      await Future<void>.delayed(Duration.zero);

      expect(notificationCount, 0);

      final updatedSelectedServer = selectedServer.copyWith(ping: 25);
      container
          .read(profileAwareStateProvider.notifier)
          .setServerListState(
            initialState.copyWith(
              servers: [updatedSelectedServer, otherServer.copyWith(ping: 95)],
            ),
          );
      await Future<void>.delayed(Duration.zero);

      expect(notificationCount, 1);
      expect(container.read(serverByIdProvider('us-1')), updatedSelectedServer);
    });

    test('serverListViewProvider ignores non-layout server updates', () async {
      final firstServer = _server(
        id: 'us-1',
        countryCode: 'US',
        countryName: 'United States',
        name: 'US 1',
        ping: 20,
      );
      final secondServer = _server(
        id: 'jp-1',
        countryCode: 'JP',
        countryName: 'Japan',
        name: 'JP 1',
        ping: 120,
      );
      final initialState = ServerListState(
        servers: [firstServer, secondServer],
        sortMode: SortMode.countryName,
        favoriteServerIds: const ['us-1'],
      );
      final profileAwareStateProvider =
          NotifierProvider<
            _ProfileAwareStateNotifier,
            AsyncValue<ServerListState>
          >(() => _ProfileAwareStateNotifier(initialState));

      final container = ProviderContainer(
        overrides: [
          profileAwareServerListProvider.overrideWith(
            (ref) => ref.watch(profileAwareStateProvider),
          ),
          importedConfigsProvider.overrideWith((ref) => const []),
        ],
      );
      addTearDown(container.dispose);

      var notificationCount = 0;
      final sub = container.listen<ServerListViewModel>(
        serverListViewProvider,
        (previous, next) => notificationCount++,
      );
      addTearDown(sub.close);

      final initialView = container.read(serverListViewProvider);
      expect(initialView.favoriteServerIds, const ['us-1']);
      expect(initialView.groupedServers.length, 2);

      container
          .read(profileAwareStateProvider.notifier)
          .setServerListState(
            initialState.copyWith(
              servers: [firstServer.copyWith(ping: 25), secondServer],
            ),
          );
      await Future<void>.delayed(Duration.zero);

      expect(notificationCount, 0);

      container
          .read(profileAwareStateProvider.notifier)
          .setServerListState(
            initialState.copyWith(
              servers: [
                firstServer.copyWith(countryCode: 'DE', countryName: 'Germany'),
                secondServer,
              ],
            ),
          );
      await Future<void>.delayed(Duration.zero);

      expect(notificationCount, 1);
      expect(container.read(serverListViewProvider).groupedServers.length, 2);
    });

    test(
      'ping-only updates do not rebuild layout but update targeted row',
      () async {
        final firstServer = _server(
          id: 'us-1',
          countryCode: 'US',
          countryName: 'United States',
          name: 'US 1',
          ping: 20,
        );
        final secondServer = _server(
          id: 'jp-1',
          countryCode: 'JP',
          countryName: 'Japan',
          name: 'JP 1',
          ping: 120,
        );
        final initialState = ServerListState(
          servers: [firstServer, secondServer],
          sortMode: SortMode.countryName,
        );
        final profileAwareStateProvider =
            NotifierProvider<
              _ProfileAwareStateNotifier,
              AsyncValue<ServerListState>
            >(() => _ProfileAwareStateNotifier(initialState));

        final container = ProviderContainer(
          overrides: [
            profileAwareServerListProvider.overrideWith(
              (ref) => ref.watch(profileAwareStateProvider),
            ),
            importedConfigsProvider.overrideWith((ref) => const []),
          ],
        );
        addTearDown(container.dispose);

        var rowNotifications = 0;
        var layoutNotifications = 0;

        final rowSub = container.listen<ServerEntity?>(
          serverByIdProvider('us-1'),
          (previous, next) => rowNotifications++,
        );
        final layoutSub = container.listen<ServerListViewModel>(
          serverListViewProvider,
          (previous, next) => layoutNotifications++,
        );
        addTearDown(rowSub.close);
        addTearDown(layoutSub.close);

        container.read(serverPingResultsProvider.notifier).mergeResults(const {
          'us-1': 33,
        });
        await Future<void>.delayed(Duration.zero);

        expect(rowNotifications, 1);
        expect(layoutNotifications, 0);
        expect(container.read(serverByIdProvider('us-1'))?.ping, 33);
      },
    );
  });
}
