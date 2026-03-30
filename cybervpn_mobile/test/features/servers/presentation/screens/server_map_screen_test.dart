import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_map_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../../helpers/mock_factories.dart';
import '../../../../helpers/test_app.dart';

void main() {
  group('ServerMapScreen', () {
    testWidgets('renders grouped country markers and opens country sheet', (
      tester,
    ) async {
      final state = ServerListState(
        servers: [
          createMockServer(
            id: 'us-1',
            name: 'US East 1',
            countryCode: 'US',
            countryName: 'United States',
            city: 'New York',
            ping: 34,
          ),
          createMockServer(
            id: 'us-2',
            name: 'US West 1',
            countryCode: 'US',
            countryName: 'United States',
            city: 'Los Angeles',
            ping: 48,
          ),
          createMockServer(
            id: 'de-1',
            name: 'Germany Frankfurt',
            countryCode: 'DE',
            countryName: 'Germany',
            city: 'Frankfurt',
            ping: 92,
          ),
        ],
      );

      await tester.pumpTestApp(
        const Scaffold(body: SizedBox.expand(child: ServerMapScreen())),
        overrides: [
          serverListProvider.overrideWith(() => _FakeServerListNotifier(state)),
          activeVpnProfileProvider.overrideWith((ref) => Stream.value(null)),
        ],
      );
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(FlutterMap), findsOneWidget);
      final markerLayer = tester.widget<MarkerLayer>(find.byType(MarkerLayer));
      expect(markerLayer.markers, hasLength(2));
      expect(
        find.byKey(const ValueKey<String>('server-map-country-US')),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);

      await tester.tap(
        find.byKey(const ValueKey<String>('server-map-country-US')),
      );
      await tester.pumpAndSettle();

      expect(find.text('United States'), findsOneWidget);
      expect(find.text('New York'), findsOneWidget);
      expect(find.text('Los Angeles'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

class _FakeServerListNotifier extends AsyncNotifier<ServerListState>
    implements ServerListNotifier {
  _FakeServerListNotifier(this._state);

  final ServerListState _state;

  @override
  Future<ServerListState> build() async => _state;

  @override
  Future<void> fetchServers() async {}

  @override
  void filterByCountry(String? countryCode) {}

  @override
  void filterByProtocol(dynamic protocol) {}

  @override
  Future<void> loadMore() async {}

  @override
  Future<void> refresh() async {}

  @override
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {}

  @override
  void sortBy(SortMode mode) {}

  @override
  Future<void> toggleFavorite(String serverId) async {}
}
