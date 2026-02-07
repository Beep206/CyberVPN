import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/profile_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/screens/connection_screen.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connect_button.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connection_info.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/shared/widgets/responsive_layout.dart';

// ---------------------------------------------------------------------------
// Overflow error suppression
// ---------------------------------------------------------------------------

void ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final exception = details.exception;
    final isOverflow = exception is FlutterError &&
        exception.message.contains('overflowed');
    if (!isOverflow) {
      FlutterError.presentError(details);
    }
  };
}

// ---------------------------------------------------------------------------
// Fake VPN connection notifier
// ---------------------------------------------------------------------------

class _FakeVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _FakeVpnConnectionNotifier(this._initialState);

  final VpnConnectionState _initialState;

  @override
  Future<VpnConnectionState> build() async => _initialState;

  @override
  Future<void> connect(ServerEntity server) async {}

  @override
  Future<void> disconnect() async {}

  @override
  Future<void> handleNetworkChange(bool isOnline) async {}

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connectToLastOrRecommended() async {}

  @override
  Future<void> connectFromCustomServer(ImportedConfig customServer) async {}
}

// ---------------------------------------------------------------------------
// Fake VPN stats notifier
// ---------------------------------------------------------------------------

class _FakeVpnStatsNotifier extends Notifier<ConnectionStatsEntity?>
    implements VpnStatsNotifier {
  _FakeVpnStatsNotifier(this._initialState);

  final ConnectionStatsEntity? _initialState;

  @override
  ConnectionStatsEntity? build() => _initialState;
}

// ---------------------------------------------------------------------------
// Fake profile notifier
// ---------------------------------------------------------------------------

class _FakeProfileNotifier extends AsyncNotifier<ProfileState>
    implements ProfileNotifier {
  _FakeProfileNotifier(this._state);

  final ProfileState _state;

  @override
  FutureOr<ProfileState> build() async => _state;

  @override
  Future<void> refreshProfile() async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Fake subscription notifier
// ---------------------------------------------------------------------------

class _FakeSubscriptionNotifier extends AsyncNotifier<SubscriptionState>
    implements SubscriptionNotifier {
  _FakeSubscriptionNotifier(this._state);

  final SubscriptionState _state;

  @override
  FutureOr<SubscriptionState> build() async => _state;

  @override
  Future<void> loadSubscription() async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testProfile = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'Test User',
  isEmailVerified: true,
  is2FAEnabled: false,
  linkedProviders: [],
  createdAt: DateTime(2024, 3, 15),
  lastLoginAt: DateTime(2025, 12, 1),
);

final _testSubscription = SubscriptionEntity(
  id: 'sub-1',
  planId: 'plan-pro',
  userId: 'user-1',
  status: SubscriptionStatus.active,
  startDate: DateTime(2025, 11, 1),
  endDate: DateTime(2026, 2, 28),
  trafficUsedBytes: 5 * 1024 * 1024 * 1024, // 5 GB
  trafficLimitBytes: 50 * 1024 * 1024 * 1024, // 50 GB
  devicesConnected: 2,
  maxDevices: 5,
);

final _testSubState = SubscriptionState(
  currentSubscription: _testSubscription,
  availablePlans: [],
  trialEligibility: false,
);

// ---------------------------------------------------------------------------
// Helper: wrap ConnectionScreen with provider overrides at a given size
// ---------------------------------------------------------------------------

Widget _buildConnectionScreen({
  required double width,
  required double height,
  VpnConnectionState vpnState = const VpnDisconnected(),
}) {
  return ProviderScope(
    overrides: [
      vpnConnectionProvider.overrideWith(
        () => _FakeVpnConnectionNotifier(vpnState),
      ),
      vpnStatsProvider.overrideWith(
        () => _FakeVpnStatsNotifier(null),
      ),
      currentServerProvider.overrideWith((ref) => null),
      activeProtocolProvider.overrideWith((ref) => null),
      isConnectedProvider.overrideWith((ref) => false),
      currentSpeedProvider.overrideWith(
        (ref) => (download: '0 B/s', upload: '0 B/s'),
      ),
      sessionUsageProvider.overrideWith(
        (ref) => (download: '0 B', upload: '0 B', total: '0 B'),
      ),
      sessionDurationProvider.overrideWith((ref) => '0s'),
    ],
    child: MediaQuery(
      data: MediaQueryData(size: Size(width, height)),
      child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('en'),
        home: SizedBox(
          width: width,
          height: height,
          child: const ConnectionScreen(),
        ),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Helper: wrap ProfileDashboardScreen with provider overrides at a given size
// ---------------------------------------------------------------------------

Widget _buildProfileDashboard({
  required double width,
  required double height,
}) {
  return ProviderScope(
    overrides: [
      profileProvider.overrideWith(
        () => _FakeProfileNotifier(ProfileState(profile: _testProfile)),
      ),
      subscriptionProvider.overrideWith(
        () => _FakeSubscriptionNotifier(_testSubState),
      ),
    ],
    child: MediaQuery(
      data: MediaQueryData(size: Size(width, height)),
      child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('en'),
        home: SizedBox(
          width: width,
          height: height,
          child: const ProfileDashboardScreen(),
        ),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(ignoreOverflowErrors);

  // =========================================================================
  // Group 1: ResponsiveLayout breakpoint helpers (unit tests)
  // =========================================================================

  group('ResponsiveLayout - breakpoint helpers', () {
    test('windowSizeClass returns compact below 600', () {
      expect(
        ResponsiveLayout.windowSizeClass(599),
        WindowSizeClass.compact,
      );
      expect(
        ResponsiveLayout.windowSizeClass(0),
        WindowSizeClass.compact,
      );
      expect(
        ResponsiveLayout.windowSizeClass(400),
        WindowSizeClass.compact,
      );
    });

    test('windowSizeClass returns medium for 600-839', () {
      expect(
        ResponsiveLayout.windowSizeClass(600),
        WindowSizeClass.medium,
      );
      expect(
        ResponsiveLayout.windowSizeClass(768),
        WindowSizeClass.medium,
      );
      expect(
        ResponsiveLayout.windowSizeClass(839),
        WindowSizeClass.medium,
      );
    });

    test('windowSizeClass returns expanded at 840 and above', () {
      expect(
        ResponsiveLayout.windowSizeClass(840),
        WindowSizeClass.expanded,
      );
      expect(
        ResponsiveLayout.windowSizeClass(1024),
        WindowSizeClass.expanded,
      );
      expect(
        ResponsiveLayout.windowSizeClass(1440),
        WindowSizeClass.expanded,
      );
    });

    test('adaptiveGridColumns returns 2 for compact', () {
      expect(ResponsiveLayout.adaptiveGridColumns(400), 2);
      expect(ResponsiveLayout.adaptiveGridColumns(599), 2);
    });

    test('adaptiveGridColumns returns 3 for medium', () {
      expect(ResponsiveLayout.adaptiveGridColumns(600), 3);
      expect(ResponsiveLayout.adaptiveGridColumns(768), 3);
    });

    test('adaptiveGridColumns returns 4 for expanded', () {
      expect(ResponsiveLayout.adaptiveGridColumns(840), 4);
      expect(ResponsiveLayout.adaptiveGridColumns(1024), 4);
    });

    test('isAtLeastMedium returns false below 600', () {
      expect(ResponsiveLayout.isAtLeastMedium(599), isFalse);
      expect(ResponsiveLayout.isAtLeastMedium(400), isFalse);
    });

    test('isAtLeastMedium returns true at 600 and above', () {
      expect(ResponsiveLayout.isAtLeastMedium(600), isTrue);
      expect(ResponsiveLayout.isAtLeastMedium(768), isTrue);
      expect(ResponsiveLayout.isAtLeastMedium(1024), isTrue);
    });
  });

  // =========================================================================
  // Group 2: ConnectionScreen responsive layout
  // =========================================================================

  group('ConnectionScreen - responsive layout', () {
    testWidgets('phone layout (400dp): widgets render correctly',
        (tester) async {
      tester.view.physicalSize = const Size(400, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildConnectionScreen(
        width: 400,
        height: 800,
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectButton), findsOneWidget);
      expect(find.byType(ConnectionInfo), findsOneWidget);
      expect(find.byType(SpeedIndicator), findsOneWidget);

      // In phone layout, ConnectButton should be above ConnectionInfo
      // (higher Y means lower on screen -- ConnectButton should have smaller dy).
      final buttonPos =
          tester.getCenter(find.byType(ConnectButton));
      final infoPos =
          tester.getCenter(find.byType(ConnectionInfo));

      expect(buttonPos.dy, lessThan(infoPos.dy),
          reason:
              'In phone Column layout, button should be above info vertically');
    });

    testWidgets(
        'tablet layout (768dp): connect button and info are side-by-side',
        (tester) async {
      tester.view.physicalSize = const Size(768, 1024);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildConnectionScreen(
        width: 768,
        height: 1024,
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectButton), findsOneWidget);
      expect(find.byType(ConnectionInfo), findsOneWidget);
      expect(find.byType(SpeedIndicator), findsOneWidget);

      // In tablet layout, ConnectButton is on the left and ConnectionInfo
      // is on the right. The ConnectButton center X should be less than
      // ConnectionInfo center X.
      final buttonPos =
          tester.getCenter(find.byType(ConnectButton));
      final infoPos =
          tester.getCenter(find.byType(ConnectionInfo));

      expect(buttonPos.dx, lessThan(infoPos.dx),
          reason: 'In tablet Row layout, button should be left of info');
    });

    testWidgets('expanded layout (1024dp): also uses side-by-side layout',
        (tester) async {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildConnectionScreen(
        width: 1024,
        height: 768,
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectButton), findsOneWidget);
      expect(find.byType(ConnectionInfo), findsOneWidget);
      expect(find.byType(SpeedIndicator), findsOneWidget);

      final buttonPos =
          tester.getCenter(find.byType(ConnectButton));
      final infoPos =
          tester.getCenter(find.byType(ConnectionInfo));

      expect(buttonPos.dx, lessThan(infoPos.dx),
          reason: 'At 1024dp, side-by-side layout should be active');
    });

    testWidgets('transition at exactly 600dp: uses tablet layout',
        (tester) async {
      tester.view.physicalSize = const Size(600, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildConnectionScreen(
        width: 600,
        height: 900,
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectButton), findsOneWidget);
      expect(find.byType(ConnectionInfo), findsOneWidget);

      final buttonPos =
          tester.getCenter(find.byType(ConnectButton));
      final infoPos =
          tester.getCenter(find.byType(ConnectionInfo));

      expect(buttonPos.dx, lessThan(infoPos.dx),
          reason: 'At exactly 600dp, tablet layout should activate');
    });

    testWidgets('phone layout at 599dp: stacked Column layout',
        (tester) async {
      tester.view.physicalSize = const Size(599, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildConnectionScreen(
        width: 599,
        height: 900,
      ));
      await tester.pumpAndSettle();

      expect(find.byType(ConnectButton), findsOneWidget);
      expect(find.byType(ConnectionInfo), findsOneWidget);

      final buttonPos =
          tester.getCenter(find.byType(ConnectButton));
      final infoPos =
          tester.getCenter(find.byType(ConnectionInfo));

      expect(buttonPos.dy, lessThan(infoPos.dy),
          reason: 'Below 600dp, phone Column layout should be used');
    });
  });

  // =========================================================================
  // Group 3: ProfileDashboardScreen adaptive grid
  // =========================================================================

  group('ProfileDashboardScreen - adaptive grid columns', () {
    testWidgets('compact width (400dp): stats grid uses 2 columns',
        (tester) async {
      tester.view.physicalSize = const Size(400, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 400,
        height: 800,
      ));
      await tester.pumpAndSettle();

      // All 4 stats cards should be present.
      expect(find.byKey(const Key('stats_plan')), findsOneWidget);
      expect(find.byKey(const Key('stats_traffic')), findsOneWidget);
      expect(find.byKey(const Key('stats_days')), findsOneWidget);
      expect(find.byKey(const Key('stats_devices')), findsOneWidget);

      // In a 2-column layout, the first two cards should share the same
      // top-Y coordinate (same row), and the 3rd card should be on the
      // next row (higher dy).
      final planPos =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));
      final trafficPos =
          tester.getTopLeft(find.byKey(const Key('stats_traffic')));
      final daysPos =
          tester.getTopLeft(find.byKey(const Key('stats_days')));

      // Cards 1 and 2 on same row.
      expect(planPos.dy, closeTo(trafficPos.dy, 1.0),
          reason: 'First 2 cards should be on the same row');
      // Card 3 on next row (larger dy).
      expect(daysPos.dy, greaterThan(planPos.dy + 10),
          reason: 'Third card should be on a second row in 2-col layout');
    });

    testWidgets('medium width (768dp): stats grid uses 3 columns',
        (tester) async {
      tester.view.physicalSize = const Size(768, 1024);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 768,
        height: 1024,
      ));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('stats_plan')), findsOneWidget);
      expect(find.byKey(const Key('stats_traffic')), findsOneWidget);
      expect(find.byKey(const Key('stats_days')), findsOneWidget);
      expect(find.byKey(const Key('stats_devices')), findsOneWidget);

      // In a 3-column layout, the first 3 cards should share the same
      // row, and the 4th card wraps to the next row.
      final planPos =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));
      final trafficPos =
          tester.getTopLeft(find.byKey(const Key('stats_traffic')));
      final daysPos =
          tester.getTopLeft(find.byKey(const Key('stats_days')));
      final devicesPos =
          tester.getTopLeft(find.byKey(const Key('stats_devices')));

      // Cards 1, 2, 3 on the same row.
      expect(planPos.dy, closeTo(trafficPos.dy, 1.0));
      expect(planPos.dy, closeTo(daysPos.dy, 1.0));
      // Card 4 on the next row.
      expect(devicesPos.dy, greaterThan(planPos.dy + 10),
          reason: 'Fourth card should wrap to next row in 3-col layout');
    });

    testWidgets('expanded width (1024dp): stats grid uses 4 columns',
        (tester) async {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 1024,
        height: 768,
      ));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('stats_plan')), findsOneWidget);
      expect(find.byKey(const Key('stats_traffic')), findsOneWidget);
      expect(find.byKey(const Key('stats_days')), findsOneWidget);
      expect(find.byKey(const Key('stats_devices')), findsOneWidget);

      // In a 4-column layout, all 4 cards should be on the same row.
      final planPos =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));
      final trafficPos =
          tester.getTopLeft(find.byKey(const Key('stats_traffic')));
      final daysPos =
          tester.getTopLeft(find.byKey(const Key('stats_days')));
      final devicesPos =
          tester.getTopLeft(find.byKey(const Key('stats_devices')));

      expect(planPos.dy, closeTo(trafficPos.dy, 1.0));
      expect(planPos.dy, closeTo(daysPos.dy, 1.0));
      expect(planPos.dy, closeTo(devicesPos.dy, 1.0),
          reason: 'All 4 cards should be on one row in 4-col layout');
    });

    testWidgets('breakpoint boundary: content width triggers column change',
        (tester) async {
      // The LayoutBuilder inside _StatsCardsGrid receives constraints
      // after ListView padding (Spacing.md = 16 on each side, 32 total).
      // So for a content width of 600dp (3-col threshold), the outer
      // screen width needs to be 600 + 32 = 632dp.

      // At 631dp: content width ~599dp -> 2 columns. Card 3 on second row.
      tester.view.physicalSize = const Size(631, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 631,
        height: 800,
      ));
      await tester.pumpAndSettle();

      final daysPos2col =
          tester.getTopLeft(find.byKey(const Key('stats_days')));
      final planPos2col =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));

      // Card 3 is on a different row than card 1 (2 cols).
      expect(daysPos2col.dy, greaterThan(planPos2col.dy + 10));

      // At 632dp: content width ~600dp -> 3 columns.
      tester.view.physicalSize = const Size(632, 800);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 632,
        height: 800,
      ));
      await tester.pumpAndSettle();

      final daysPos3col =
          tester.getTopLeft(find.byKey(const Key('stats_days')));
      final planPos3col =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));

      // Card 3 is on the same row as card 1 (3 cols).
      expect(daysPos3col.dy, closeTo(planPos3col.dy, 1.0),
          reason: 'When content width reaches 600dp, 3 columns should '
              'place card 3 on the first row');
    });

    testWidgets('breakpoint boundary: content width 840dp triggers 4 columns',
        (tester) async {
      // Same padding offset: 840 + 32 = 872dp screen width for 4-col.

      // At 871dp: content width ~839dp -> 3 columns. Card 4 on second row.
      tester.view.physicalSize = const Size(871, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 871,
        height: 800,
      ));
      await tester.pumpAndSettle();

      final devicesPos3col =
          tester.getTopLeft(find.byKey(const Key('stats_devices')));
      final planPos3col =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));

      // Card 4 is on a different row (3 cols).
      expect(devicesPos3col.dy, greaterThan(planPos3col.dy + 10));

      // At 872dp: content width ~840dp -> 4 columns.
      tester.view.physicalSize = const Size(872, 800);

      await tester.pumpWidget(_buildProfileDashboard(
        width: 872,
        height: 800,
      ));
      await tester.pumpAndSettle();

      final devicesPos4col =
          tester.getTopLeft(find.byKey(const Key('stats_devices')));
      final planPos4col =
          tester.getTopLeft(find.byKey(const Key('stats_plan')));

      // Card 4 is on the same row as card 1 (4 cols).
      expect(devicesPos4col.dy, closeTo(planPos4col.dy, 1.0),
          reason: 'When content width reaches 840dp, 4 columns should '
              'place all cards on the first row');
    });
  });
}
