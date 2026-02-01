import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/profile_dashboard_screen.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testProfile = Profile(
  id: 'user-1',
  email: 'john.doe@example.com',
  username: 'John Doe',
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
// Fake profile notifier
// ---------------------------------------------------------------------------

class _FakeProfileNotifier extends AsyncNotifier<ProfileState>
    implements ProfileNotifier {
  _FakeProfileNotifier(this._state);

  final ProfileState _state;
  bool refreshCalled = false;

  @override
  FutureOr<ProfileState> build() async => _state;

  @override
  Future<void> refreshProfile() async {
    refreshCalled = true;
  }

  // Stubs for methods not used in dashboard tests.
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
  bool loadSubscriptionCalled = false;

  @override
  FutureOr<SubscriptionState> build() async => _state;

  @override
  Future<void> loadSubscription() async {
    loadSubscriptionCalled = true;
  }

  // Stubs for methods not used in dashboard tests.
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Helper: build widget under test
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required ProfileState profileState,
  SubscriptionState? subState,
  _FakeProfileNotifier? profileNotifier,
  _FakeSubscriptionNotifier? subNotifier,
}) {
  final pNotifier = profileNotifier ?? _FakeProfileNotifier(profileState);
  final sNotifier = subNotifier ??
      _FakeSubscriptionNotifier(
        subState ?? const SubscriptionState(),
      );

  return ProviderScope(
    overrides: [
      profileProvider.overrideWith(() => pNotifier),
      subscriptionProvider.overrideWith(() => sNotifier),
    ],
    child: const MaterialApp(
      home: ProfileDashboardScreen(),
    ),
  );
}

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
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(ignoreOverflowErrors);

  // =========================================================================
  // Group 1: Profile header rendering
  // =========================================================================

  group('ProfileDashboardScreen - header', () {
    testWidgets('renders username and email', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.text('John Doe'), findsOneWidget);
      expect(find.text('john.doe@example.com'), findsOneWidget);
    });

    testWidgets('renders initials in avatar', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      // Initials for "John Doe" should be "JD"
      expect(find.text('JD'), findsOneWidget);
    });

    testWidgets('renders member since date', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.textContaining('Member since'), findsOneWidget);
      expect(find.textContaining('March 2024'), findsOneWidget);
    });

    testWidgets('greeting text is present', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      // One of these greetings should appear based on test time.
      final hasGreeting = find.text('Good morning').evaluate().isNotEmpty ||
          find.text('Good afternoon').evaluate().isNotEmpty ||
          find.text('Good evening').evaluate().isNotEmpty;
      expect(hasGreeting, isTrue);
    });
  });

  // =========================================================================
  // Group 2: Stats cards
  // =========================================================================

  group('ProfileDashboardScreen - stats cards', () {
    testWidgets('renders all 4 stats cards with subscription', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('stats_plan')), findsOneWidget);
      expect(find.byKey(const Key('stats_traffic')), findsOneWidget);
      expect(find.byKey(const Key('stats_days')), findsOneWidget);
      expect(find.byKey(const Key('stats_devices')), findsOneWidget);
    });

    testWidgets('displays Active plan status', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.text('Active'), findsOneWidget);
    });

    testWidgets('displays device count', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.text('2 / 5'), findsOneWidget);
    });

    testWidgets('displays placeholder when no subscription', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: const SubscriptionState(),
      ));
      await tester.pumpAndSettle();

      expect(find.text('No Plan'), findsOneWidget);
      // Days and devices show dashes when no subscription.
      expect(find.text('--'), findsAtLeast(1));
    });
  });

  // =========================================================================
  // Group 3: Quick actions
  // =========================================================================

  group('ProfileDashboardScreen - quick actions', () {
    testWidgets('renders all 3 quick action buttons', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('action_upgrade')), findsOneWidget);
      expect(find.byKey(const Key('action_invite')), findsOneWidget);
      expect(find.byKey(const Key('action_security')), findsOneWidget);
    });

    testWidgets('renders quick action labels', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.text('Upgrade Plan'), findsOneWidget);
      expect(find.text('Invite Friends'), findsOneWidget);
      expect(find.text('Security Settings'), findsOneWidget);
    });

    testWidgets('renders Quick Actions section title', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
      ));
      await tester.pumpAndSettle();

      expect(find.text('Quick Actions'), findsOneWidget);
    });
  });

  // =========================================================================
  // Group 4: Pull-to-refresh
  // =========================================================================

  group('ProfileDashboardScreen - pull to refresh', () {
    testWidgets('pull-to-refresh triggers provider refresh', (tester) async {
      final profileNotifier =
          _FakeProfileNotifier(ProfileState(profile: _testProfile));
      final subNotifier = _FakeSubscriptionNotifier(_testSubState);

      await tester.pumpWidget(_buildTestWidget(
        profileState: ProfileState(profile: _testProfile),
        subState: _testSubState,
        profileNotifier: profileNotifier,
        subNotifier: subNotifier,
      ));
      await tester.pumpAndSettle();

      // Perform pull-to-refresh gesture.
      await tester.fling(
        find.byType(ListView),
        const Offset(0, 300),
        1000,
      );
      await tester.pumpAndSettle();

      expect(profileNotifier.refreshCalled, isTrue);
      expect(subNotifier.loadSubscriptionCalled, isTrue);
    });
  });

  // =========================================================================
  // Group 5: Loading and error states
  // =========================================================================

  group('ProfileDashboardScreen - loading/error', () {
    testWidgets('shows loading indicator when profile is loading',
        (tester) async {
      // Use a notifier that never completes.
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileProvider.overrideWith(_NeverCompleteProfileNotifier.new),
            subscriptionProvider.overrideWith(
              () => _FakeSubscriptionNotifier(const SubscriptionState()),
            ),
          ],
          child: const MaterialApp(
            home: ProfileDashboardScreen(),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}

// ---------------------------------------------------------------------------
// Helper: never-completing profile notifier (for loading state test)
// ---------------------------------------------------------------------------

class _NeverCompleteProfileNotifier extends AsyncNotifier<ProfileState>
    implements ProfileNotifier {
  @override
  FutureOr<ProfileState> build() {
    // Return a future that never completes to keep the loading state.
    return Completer<ProfileState>().future;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
