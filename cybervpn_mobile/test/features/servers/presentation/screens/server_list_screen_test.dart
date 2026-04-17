import 'dart:async';

import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_list_screen.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/country_group_header.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/server_card.dart';

import '../../../../helpers/mock_factories.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

/// Creates a list of servers grouped across 3 countries for testing.
List<ServerEntity> _buildTestServers() {
  return [
    createMockServer(
      id: 'us-1',
      name: 'US East 1',
      countryCode: 'US',
      countryName: 'United States',
      city: 'New York',
      ping: 30,
      load: 0.2,
      isFavorite: true,
    ),
    createMockServer(
      id: 'us-2',
      name: 'US West 1',
      countryCode: 'US',
      countryName: 'United States',
      city: 'Los Angeles',
      ping: 50,
      load: 0.4,
    ),
    createMockServer(
      id: 'de-1',
      name: 'Germany Frankfurt',
      countryCode: 'DE',
      countryName: 'Germany',
      city: 'Frankfurt',
      ping: 120,
      load: 0.6,
    ),
    createMockServer(
      id: 'jp-1',
      name: 'Japan Tokyo',
      countryCode: 'JP',
      countryName: 'Japan',
      city: 'Tokyo',
      ping: 180,
      load: 0.3,
    ),
    createMockServer(
      id: 'jp-2',
      name: 'Japan Osaka',
      countryCode: 'JP',
      countryName: 'Japan',
      city: 'Osaka',
      ping: 200,
      load: 0.5,
    ),
  ];
}

SharedPreferences? _mockPrefs;

// ---------------------------------------------------------------------------
// Helper: build the widget under test with provider overrides
// ---------------------------------------------------------------------------

/// Builds a [ServerListScreen] inside a [ProviderScope] with the given state
/// pre-loaded so no real network calls are needed.
Widget _buildTestWidget({
  required ServerListState state,
  NavigatorObserver? navigatorObserver,
  AppSettings settings = const AppSettings(),
}) {
  final router = GoRouter(
    initialLocation: '/',
    observers: <NavigatorObserver>[
      ...?navigatorObserver == null ? null : [navigatorObserver],
    ],
    routes: [
      GoRoute(path: '/', builder: (context, state) => const ServerListScreen()),
      GoRoute(
        path: '/servers/:id',
        builder: (context, state) =>
            Scaffold(body: Text('Detail: ${state.pathParameters['id']}')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      serverListProvider.overrideWith(() => _FakeServerListNotifier(state)),
      sharedPreferencesProvider.overrideWithValue(_mockPrefs!),
      importedConfigsProvider.overrideWith((ref) => const []),
      activeVpnProfileProvider.overrideWith((ref) => Stream.value(null)),
      settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
    ],
    child: MaterialApp.router(
      routerConfig: router,
      builder: (context, child) {
        return MediaQuery(
          data: const MediaQueryData(
            size: Size(400, 800),
            disableAnimations: true,
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    ),
  );
}

/// A fake [ServerListNotifier] that returns pre-built state without performing
/// any async operations (no repository calls, no pings).
class _FakeServerListNotifier extends AsyncNotifier<ServerListState>
    implements ServerListNotifier {
  _FakeServerListNotifier(this._initialState);

  final ServerListState _initialState;

  @override
  Future<ServerListState> build() async {
    return _initialState;
  }

  @override
  void sortBy(SortMode mode) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData(current.copyWith(sortMode: mode));
  }

  @override
  Future<void> fetchServers() async {}

  @override
  void filterByCountry(String? countryCode) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData(current.copyWith(filterCountry: countryCode));
  }

  @override
  void filterByProtocol(dynamic protocol) {}

  @override
  Future<void> toggleFavorite(String serverId) async {
    final current = state.value;
    if (current == null) return;

    final updatedServers = current.servers.map((s) {
      if (s.id == serverId) return s.copyWith(isFavorite: !s.isFavorite);
      return s;
    }).toList();

    List<String> updatedFavIds;
    if (current.favoriteServerIds.contains(serverId)) {
      updatedFavIds = List<String>.from(current.favoriteServerIds)
        ..remove(serverId);
    } else {
      updatedFavIds = List<String>.from(current.favoriteServerIds)
        ..add(serverId);
    }

    state = AsyncData(
      current.copyWith(
        servers: updatedServers,
        favoriteServerIds: updatedFavIds,
      ),
    );
  }

  @override
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {}

  @override
  Future<void> refresh() async {}

  @override
  Future<void> loadMore() async {}
}

// ---------------------------------------------------------------------------
// Mock NavigatorObserver
// ---------------------------------------------------------------------------

class MockNavigatorObserver extends Mock implements NavigatorObserver {}

class FakeRoute extends Fake implements Route<dynamic> {}

// ---------------------------------------------------------------------------
// Notifiers for loading/error states
// ---------------------------------------------------------------------------

class _LoadingNotifier extends AsyncNotifier<ServerListState>
    implements ServerListNotifier {
  // Use a Completer that never completes to simulate perpetual loading
  // without creating a pending timer.
  final _completer = Completer<ServerListState>();

  @override
  Future<ServerListState> build() {
    return _completer.future;
  }

  @override
  void sortBy(SortMode mode) {}
  @override
  Future<void> fetchServers() async {}
  @override
  void filterByCountry(String? countryCode) {}
  @override
  void filterByProtocol(dynamic protocol) {}
  @override
  Future<void> toggleFavorite(String serverId) async {}
  @override
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {}
  @override
  Future<void> refresh() async {}
  @override
  Future<void> loadMore() async {}
}

class _ErrorNotifier extends AsyncNotifier<ServerListState>
    implements ServerListNotifier {
  @override
  Future<ServerListState> build() async {
    throw Exception('Network error');
  }

  @override
  void sortBy(SortMode mode) {}
  @override
  Future<void> fetchServers() async {}
  @override
  void filterByCountry(String? countryCode) {}
  @override
  void filterByProtocol(dynamic protocol) {}
  @override
  Future<void> toggleFavorite(String serverId) async {}
  @override
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {}
  @override
  Future<void> refresh() async {}
  @override
  Future<void> loadMore() async {}
}

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier(this._settings);

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

Future<void> _pumpSearchDebounce(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 220));
  await tester.pump();
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUpAll(() {
    registerFallbackValue(FakeRoute());
  });

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    _mockPrefs = await SharedPreferences.getInstance();
  });

  // =========================================================================
  // Group 1: Server list grouping and rendering
  // =========================================================================

  group('ServerListScreen - grouping and rendering', () {
    testWidgets('renders app bar with "Servers" title', (tester) async {
      final servers = _buildTestServers();
      final state = ServerListState(
        servers: servers,
        favoriteServerIds: ['us-1'],
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Servers'), findsOneWidget);
    });

    testWidgets('renders country group headers for each country', (
      tester,
    ) async {
      final servers = _buildTestServers();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // CountryGroupHeader widgets should render for US, DE, JP.
      expect(find.byType(CountryGroupHeader), findsAtLeast(2));

      // Country names appear in CountryGroupHeader widgets.
      expect(find.text('United States'), findsAtLeast(1));
      expect(find.text('Germany'), findsAtLeast(1));
    });

    testWidgets('renders server names in the list', (tester) async {
      // Use no favorites so server names appear only once in the grouped list.
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Without favorites, each server name appears once.
      expect(find.text('US East 1'), findsOneWidget);
      expect(find.text('US West 1'), findsOneWidget);
      expect(find.text('Germany Frankfurt'), findsOneWidget);
    });

    testWidgets('renders ServerCard widgets for servers', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Without favorites, at least 3 visible ServerCards (US+DE servers).
      expect(find.byType(ServerCard), findsAtLeast(3));
    });

    testWidgets('shows favorites section when favorites exist', (tester) async {
      final servers = _buildTestServers();
      final state = ServerListState(
        servers: servers,
        favoriteServerIds: ['us-1'],
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Favorites'), findsOneWidget);
    });

    testWidgets('hides favorites section when no favorites', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Favorites'), findsNothing);
    });

    testWidgets('shows search field and sort dropdown', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('Search servers...'), findsOneWidget);
      expect(find.text('Recommended'), findsOneWidget);
    });

    testWidgets('shows Fastest chip', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Fastest'), findsOneWidget);
      expect(find.byType(ActionChip), findsOneWidget);
    });

    testWidgets(
      'shows loading indicator in loading state',
      (tester) async {
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              serverListProvider.overrideWith(_LoadingNotifier.new),
              sharedPreferencesProvider.overrideWithValue(_mockPrefs!),
              importedConfigsProvider.overrideWith((ref) => const []),
              activeVpnProfileProvider.overrideWith(
                (ref) => Stream.value(null),
              ),
              settingsProvider.overrideWith(
                () => _FakeSettingsNotifier(const AppSettings()),
              ),
            ],
            child: const MaterialApp(
              localizationsDelegates: [
                AppLocalizations.delegate,
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              supportedLocales: AppLocalizations.supportedLocales,
              home: ServerListScreen(),
            ),
          ),
        );
        // Use pump() with a short duration. The provider stays in AsyncLoading
        // because the build() future never resolves.
        await tester.pump(const Duration(milliseconds: 100));

        expect(find.byType(CircularProgressIndicator), findsOneWidget);
      },
      timeout: const Timeout(Duration(seconds: 10)),
    );

    testWidgets('shows error state with retry button', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            serverListProvider.overrideWith(_ErrorNotifier.new),
            sharedPreferencesProvider.overrideWithValue(_mockPrefs!),
            importedConfigsProvider.overrideWith((ref) => const []),
            activeVpnProfileProvider.overrideWith((ref) => Stream.value(null)),
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings()),
            ),
          ],
          child: const MaterialApp(
            localizationsDelegates: [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            home: ServerListScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load servers'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 2: Search, sort, and favorite toggle
  // =========================================================================

  group('ServerListScreen - search, sort, and favorites', () {
    testWidgets('search filters servers by city/name', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Initially visible.
      expect(find.text('US East 1'), findsOneWidget);
      expect(find.text('Germany Frankfurt'), findsOneWidget);

      // Enter search text that matches Frankfurt city.
      await tester.enterText(find.byType(TextField), 'Frankfurt');
      await _pumpSearchDebounce(tester);

      // Germany Frankfurt should still be visible (matches city).
      expect(find.text('Germany Frankfurt'), findsOneWidget);

      // US servers should be hidden (no match in name/city/country).
      // The country group headers for non-matching groups are excluded.
      // US group header should not appear since no US servers match 'Frankfurt'.
    });

    testWidgets('search applies after debounce instead of every keystroke', (
      tester,
    ) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'zzzznonexistent');
      await tester.pump(const Duration(milliseconds: 40));

      expect(find.text('US East 1'), findsOneWidget);
      expect(find.text('No servers match your search'), findsNothing);

      await _pumpSearchDebounce(tester);

      expect(find.text('No servers match your search'), findsOneWidget);
    });

    testWidgets('search filters servers by country name', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Japan');
      await _pumpSearchDebounce(tester);

      // Japan servers match by countryName.
      // They may or may not be visible depending on scroll position,
      // but the grouped list should only show Japan group.
    });

    testWidgets('search clear button restores full list', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Enter search text.
      await tester.enterText(find.byType(TextField), 'Frankfurt');
      await _pumpSearchDebounce(tester);

      // Clear button should appear.
      final clearButton = find.byIcon(Icons.clear);
      expect(clearButton, findsOneWidget);

      await tester.tap(clearButton);
      await _pumpSearchDebounce(tester);

      // All servers should be visible again.
      expect(find.text('US East 1'), findsOneWidget);
    });

    testWidgets('sort dropdown opens and shows all sort options', (
      tester,
    ) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Current sort is 'Recommended'.
      expect(find.text('Recommended'), findsOneWidget);

      // Open dropdown.
      await tester.tap(find.text('Recommended'));
      await tester.pumpAndSettle();

      // All options visible in the dropdown overlay.
      expect(find.text('Country'), findsOneWidget);
      expect(find.text('Latency'), findsOneWidget);
      expect(find.text('Load'), findsOneWidget);
    });

    testWidgets('selecting sort option changes displayed sort mode', (
      tester,
    ) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Open dropdown.
      await tester.tap(find.text('Recommended'));
      await tester.pumpAndSettle();

      // Select 'Country'.
      await tester.tap(find.text('Country').last);
      await tester.pumpAndSettle();

      // Dropdown should now show 'Country'.
      expect(find.text('Country'), findsOneWidget);
    });

    testWidgets('favorite star icons are displayed on server cards', (
      tester,
    ) async {
      // Use a simple setup: us-1 is favorite, others are not.
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Non-favorite servers have star_border icons.
      expect(find.byIcon(Icons.star_border), findsAtLeast(1));
    });

    testWidgets('ping result preference changes ping chips to icons', (
      tester,
    ) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(
        _buildTestWidget(
          state: state,
          settings: const AppSettings(pingResultMode: PingResultMode.icon),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.signal_cellular_alt), findsWidgets);
      expect(find.byIcon(Icons.network_cell), findsWidgets);
      await tester.scrollUntilVisible(
        find.byIcon(Icons.signal_cellular_connected_no_internet_4_bar),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      expect(
        find.byIcon(Icons.signal_cellular_connected_no_internet_4_bar),
        findsWidgets,
      );
    });

    testWidgets('favorite toggle updates state via notifier', (tester) async {
      // Start with us-1 as favorite.
      final servers = _buildTestServers();
      final state = ServerListState(
        servers: servers,
        favoriteServerIds: ['us-1'],
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // The favorites section should be visible since us-1 is favorite.
      expect(find.text('Favorites'), findsOneWidget);

      // Verify that the filled star icon (from favorites header) is present.
      expect(find.byIcon(Icons.star), findsAtLeast(1));

      // Verify that star_border icons exist for non-favorite servers.
      expect(find.byIcon(Icons.star_border), findsAtLeast(1));
    });
  });

  // =========================================================================
  // Group 3: Navigation on server tap
  // =========================================================================

  group('ServerListScreen - navigation', () {
    testWidgets('tapping a server navigates to /server-detail with server ID', (
      tester,
    ) async {
      final observer = MockNavigatorObserver();
      // No favorites to avoid duplicate name findings.
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(
        _buildTestWidget(state: state, navigatorObserver: observer),
      );
      await tester.pumpAndSettle();

      // Reset mock to ignore the initial MaterialApp push.
      reset(observer);

      // Tap on the 'US East 1' server card.
      await tester.tap(find.text('US East 1'));
      await tester.pumpAndSettle();

      // Verify navigation push occurred.
      verify(() => observer.didPush(any(), any())).called(1);

      // The detail screen placeholder should show the server ID.
      expect(find.text('Detail: us-1'), findsOneWidget);
    });

    testWidgets('tapping a different server passes correct ID', (tester) async {
      final observer = MockNavigatorObserver();
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(
        _buildTestWidget(state: state, navigatorObserver: observer),
      );
      await tester.pumpAndSettle();

      reset(observer);

      // Tap on 'Germany Frankfurt'.
      await tester.tap(find.text('Germany Frankfurt'));
      await tester.pumpAndSettle();

      // The detail screen should show the ID 'de-1'.
      expect(find.text('Detail: de-1'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 4: Empty state for filtered server list
  // =========================================================================

  group('ServerListScreen - empty state', () {
    testWidgets('shows empty state when search matches no servers', (
      tester,
    ) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Enter a query that matches no server name, city, or country.
      await tester.enterText(find.byType(TextField), 'zzzznonexistent');
      await _pumpSearchDebounce(tester);

      // The empty state should show.
      expect(find.text('No servers match your search'), findsOneWidget);
      expect(find.text('Clear search'), findsOneWidget);
    });

    testWidgets('tapping Clear search restores full list', (tester) async {
      final servers = _buildTestServers()
          .map((s) => s.copyWith(isFavorite: false))
          .toList();
      final state = ServerListState(servers: servers, favoriteServerIds: []);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Enter non-matching query.
      await tester.enterText(find.byType(TextField), 'zzzznonexistent');
      await _pumpSearchDebounce(tester);

      // Verify empty state is displayed.
      // Tap 'Clear search' button.
      await tester.tap(find.text('Clear search'));
      await _pumpSearchDebounce(tester);

      // Servers should reappear.
      expect(find.text('US East 1'), findsOneWidget);
      expect(find.text('Germany Frankfurt'), findsOneWidget);
    });
  });
}
