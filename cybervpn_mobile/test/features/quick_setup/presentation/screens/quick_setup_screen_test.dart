import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/quick_setup/presentation/screens/quick_setup_screen.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late SharedPreferences mockPrefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    mockPrefs = await SharedPreferences.getInstance();
  });

  Widget buildQuickSetupHost({
    required SharedPreferences prefs,
    required TestVpnConnectionNotifier vpnNotifier,
    ServerEntity? recommendedServer,
  }) {
    final router = GoRouter(
      initialLocation: '/quick-setup',
      routes: [
        GoRoute(
          path: '/quick-setup',
          builder: (context, state) => const QuickSetupScreen(),
        ),
        GoRoute(
          path: '/connection',
          builder: (context, state) =>
              const Scaffold(body: Text('Connection destination')),
        ),
        GoRoute(
          path: '/servers',
          builder: (context, state) =>
              const Scaffold(body: Text('Servers destination')),
        ),
      ],
    );

    return ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        recommendedServerProvider.overrideWith((ref) => recommendedServer),
        vpnConnectionProvider.overrideWith(() => vpnNotifier),
      ],
      child: MaterialApp.router(
        routerConfig: router,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('en'),
      ),
    );
  }

  Future<void> pumpQuickSetupScreen(
    WidgetTester tester, {
    required TestVpnConnectionNotifier vpnNotifier,
    ServerEntity? recommendedServer,
  }) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(430, 1200));
    await tester.pumpWidget(
      buildQuickSetupHost(
        prefs: mockPrefs,
        vpnNotifier: vpnNotifier,
        recommendedServer: recommendedServer,
      ),
    );
    await tester.pump(const Duration(milliseconds: 50));
  }

  const server = ServerEntity(
    id: 'server-1',
    name: 'US East 1',
    countryCode: 'US',
    countryName: 'United States',
    city: 'New York',
    address: '1.2.3.4',
    port: 443,
    protocol: 'vless',
    isAvailable: true,
    isPremium: false,
    isFavorite: false,
    ping: 25,
  );

  testWidgets(
    'displays auto-selected server with country flag and server name',
    (tester) async {
      await pumpQuickSetupScreen(
        tester,
        vpnNotifier: TestVpnConnectionNotifier(const VpnDisconnected()),
        recommendedServer: server,
      );

      expect(find.text('Ready to protect you'), findsOneWidget);
      expect(find.text('US East 1'), findsOneWidget);
      expect(find.text('New York, United States'), findsOneWidget);
      expect(find.text('25 ms'), findsOneWidget);
      expect(find.text('Connect Now'), findsOneWidget);
    },
  );

  testWidgets('taps Connect and calls VPN provider connect', (tester) async {
    final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

    await pumpQuickSetupScreen(
      tester,
      vpnNotifier: vpnNotifier,
      recommendedServer: server,
    );

    await tester.tap(find.text('Connect Now'));
    await tester.pump();

    expect(vpnNotifier.connectCalled, isTrue);
    expect(vpnNotifier.lastConnectedServer?.id, equals('server-1'));
  });

  testWidgets(
    'shows celebration animation and navigates to connection screen on success',
    (tester) async {
      final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

      await pumpQuickSetupScreen(
        tester,
        vpnNotifier: vpnNotifier,
        recommendedServer: server,
      );

      await tester.tap(find.text('Connect Now'));
      await tester.pump();

      vpnNotifier.setState(
        const VpnConnected(server: server, protocol: VpnProtocol.vless),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('You\'re protected!'), findsOneWidget);
      expect(find.text('Your connection is now secure'), findsOneWidget);

      await tester.pump(const Duration(milliseconds: 2100));
      await tester.pump();
      expect(find.text('Connection destination'), findsOneWidget);
    },
  );

  testWidgets(
    'displays loading indicator when no recommended server is available',
    (tester) async {
      await pumpQuickSetupScreen(
        tester,
        vpnNotifier: TestVpnConnectionNotifier(const VpnDisconnected()),
        recommendedServer: null,
      );

      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(find.text('Finding the best server...'), findsOneWidget);

      final connectButton = tester.widget<ElevatedButton>(
        find.byType(ElevatedButton).first,
      );
      expect(connectButton.onPressed, isNull);
    },
  );

  testWidgets('shows error SnackBar on connection failure', (tester) async {
    final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

    await pumpQuickSetupScreen(
      tester,
      vpnNotifier: vpnNotifier,
      recommendedServer: server,
    );

    await tester.tap(find.text('Connect Now'));
    await tester.pump();

    vpnNotifier.setState(const VpnError(message: 'Connection timed out'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(
      find.text('Connection failed: Connection timed out'),
      findsOneWidget,
    );

    await tester.pump(const Duration(seconds: 3));
    await tester.pump();
    expect(find.text('Servers destination'), findsOneWidget);
  });

  testWidgets('marks setup as abandoned when skip button is tapped', (
    tester,
  ) async {
    await pumpQuickSetupScreen(
      tester,
      vpnNotifier: TestVpnConnectionNotifier(const VpnDisconnected()),
      recommendedServer: server,
    );

    await tester.ensureVisible(find.text('Skip for now'));
    await tester.tap(find.text('Skip for now'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 20));

    expect(mockPrefs.getBool('quick_setup_abandoned'), isTrue);
    expect(mockPrefs.getBool('quick_setup_completed'), isTrue);
    expect(find.text('Connection destination'), findsOneWidget);
  });

  testWidgets('shows loading indicator during connection attempt', (
    tester,
  ) async {
    final vpnNotifier = TestVpnConnectionNotifier(const VpnDisconnected());

    await pumpQuickSetupScreen(
      tester,
      vpnNotifier: vpnNotifier,
      recommendedServer: server,
    );

    await tester.tap(find.text('Connect Now'));
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsWidgets);
  });
}

class TestVpnConnectionNotifier extends VpnConnectionNotifier {
  TestVpnConnectionNotifier(this.initialState);

  final VpnConnectionState? initialState;
  bool connectCalled = false;
  ServerEntity? lastConnectedServer;

  @override
  Future<VpnConnectionState> build() async {
    return initialState ?? const VpnDisconnected();
  }

  @override
  Future<void> connect(ServerEntity server) async {
    connectCalled = true;
    lastConnectedServer = server;
    state = AsyncData(VpnConnecting(server: server));
  }

  @override
  Future<void> disconnect() async {
    state = const AsyncData(VpnDisconnecting());
  }

  @override
  Future<void> handleNetworkChange(bool isOnline) async {}

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connectToLastOrRecommended() async {}

  void setState(VpnConnectionState newState) {
    state = AsyncData(newState);
  }
}
