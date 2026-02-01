import 'dart:async';

import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';
import 'package:cybervpn_mobile/features/referral/domain/repositories/referral_repository.dart';
import 'package:cybervpn_mobile/features/referral/presentation/providers/referral_provider.dart';
import 'package:cybervpn_mobile/features/referral/presentation/screens/referral_dashboard_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockReferralRepository extends Mock implements ReferralRepository {}

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const _sampleStats = ReferralStats(
  totalInvited: 10,
  paidUsers: 3,
  pointsEarned: 250.0,
  balance: 120.50,
);

final _sampleReferrals = [
  ReferralEntry(
    code: 'REF001',
    joinDate: DateTime(2025, 6, 1),
    status: ReferralStatus.active,
  ),
  ReferralEntry(
    code: 'REF002',
    joinDate: DateTime(2025, 7, 15),
    status: ReferralStatus.completed,
  ),
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Wraps [ReferralDashboardScreen] with required providers for testing.
/// Uses a large screen size to avoid scroll issues in tests.
Widget buildTestWidget(MockReferralRepository mockRepo) {
  return ProviderScope(
    overrides: [
      referralRepositoryProvider.overrideWithValue(mockRepo),
    ],
    child: const MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(size: Size(400, 1200)),
        child: ReferralDashboardScreen(),
      ),
    ),
  );
}

void _stubAvailable(MockReferralRepository mockRepo) {
  when(() => mockRepo.isAvailable()).thenAnswer((_) async => true);
  when(() => mockRepo.getReferralCode())
      .thenAnswer((_) async => 'CYBER123');
  when(() => mockRepo.getStats()).thenAnswer((_) async => _sampleStats);
  when(() => mockRepo.getRecentReferrals())
      .thenAnswer((_) async => _sampleReferrals);
}

void _stubUnavailable(MockReferralRepository mockRepo) {
  when(() => mockRepo.isAvailable()).thenAnswer((_) async => false);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockReferralRepository mockRepo;

  setUp(() {
    mockRepo = MockReferralRepository();
  });

  group('ReferralDashboardScreen - available state', () {
    testWidgets('renders referral code card with code text', (tester) async {
      _stubAvailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      // Verify the referral code is displayed.
      expect(find.text('CYBER123'), findsOneWidget);

      // Verify the section title.
      expect(find.text('Your Referral Code'), findsOneWidget);
    });

    testWidgets('renders stats cards with correct values', (tester) async {
      _stubAvailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      // Verify stats section title.
      expect(find.text('Your Stats'), findsOneWidget);

      // Verify stat values.
      expect(find.text('10'), findsOneWidget); // totalInvited
      expect(find.text('3'), findsOneWidget); // paidUsers
      expect(find.text('250'), findsOneWidget); // pointsEarned
      expect(find.text('\$120.50'), findsOneWidget); // balance
    });

    testWidgets('renders recent referrals list', (tester) async {
      tester.view.physicalSize = const Size(400, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      _stubAvailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      // Verify section title.
      expect(find.text('Recent Referrals'), findsOneWidget);

      // Verify referral entries.
      expect(find.text('REF001'), findsOneWidget);
      expect(find.text('REF002'), findsOneWidget);

      // Verify status chips.
      expect(find.text('Active'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
    });

    testWidgets('copy button exists and is tappable', (tester) async {
      _stubAvailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      final copyButton = find.byKey(const Key('btn_copy_code'));
      expect(copyButton, findsOneWidget);

      // Tap the copy button -- verifying it does not throw.
      await tester.tap(copyButton);
      await tester.pump();
      // The snackbar may or may not appear depending on Clipboard test binding
      // availability. The key assertion is that the button is present and
      // tappable without errors.
    });

    testWidgets('share button exists', (tester) async {
      _stubAvailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      final shareButton = find.byKey(const Key('btn_share_code'));
      expect(shareButton, findsOneWidget);
    });

    testWidgets('refresh button triggers provider refresh', (tester) async {
      _stubAvailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      final refreshButton = find.byKey(const Key('btn_refresh_referral'));
      expect(refreshButton, findsOneWidget);

      // Tap refresh - should call isAvailable again.
      await tester.tap(refreshButton);
      await tester.pumpAndSettle();

      // isAvailable is called once on build and once on refresh.
      verify(() => mockRepo.isAvailable()).called(greaterThanOrEqualTo(2));
    });
  });

  group('ReferralDashboardScreen - unavailable state', () {
    testWidgets('shows Coming Soon placeholder when unavailable',
        (tester) async {
      _stubUnavailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      // Verify coming soon content.
      expect(
        find.text('Referral Program Coming Soon'),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('btn_notify_me')),
        findsOneWidget,
      );
    });

    testWidgets('Notify Me button shows confirmation SnackBar',
        (tester) async {
      _stubUnavailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('btn_notify_me')));
      await tester.pumpAndSettle();

      expect(
        find.text("We'll notify you when referrals launch!"),
        findsOneWidget,
      );
    });

    testWidgets('does not render referral code or stats when unavailable',
        (tester) async {
      _stubUnavailable(mockRepo);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      await tester.pumpAndSettle();

      expect(find.text('Your Referral Code'), findsNothing);
      expect(find.text('Your Stats'), findsNothing);
      expect(find.text('Recent Referrals'), findsNothing);
    });
  });

  group('ReferralDashboardScreen - loading state', () {
    testWidgets('shows loading indicator while data loads', (tester) async {
      // Use a completer to hold the future in loading state without timers.
      final completer = Completer<bool>();
      when(() => mockRepo.isAvailable())
          .thenAnswer((_) => completer.future);

      await tester.pumpWidget(buildTestWidget(mockRepo));
      // Pump once without settling to see loading state.
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Complete to avoid pending timer issues.
      completer.complete(false);
      await tester.pumpAndSettle();
    });
  });
}
