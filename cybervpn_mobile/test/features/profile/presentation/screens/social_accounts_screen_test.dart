import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/social_accounts_screen.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testProfileNotLinked = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  isEmailVerified: true,
  is2FAEnabled: false,
  linkedProviders: [],
  createdAt: DateTime(2024, 1, 1),
);

final _testProfileLinked = Profile(
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  telegramId: 'telegram_user',
  isEmailVerified: true,
  is2FAEnabled: false,
  linkedProviders: [OAuthProvider.telegram],
  createdAt: DateTime(2024, 1, 1),
);

// ---------------------------------------------------------------------------
// Fake profile notifier
// ---------------------------------------------------------------------------

class _FakeProfileNotifier extends AsyncNotifier<ProfileState>
    implements ProfileNotifier {
  _FakeProfileNotifier(this._state);

  final ProfileState _state;

  @override
  FutureOr<ProfileState> build() async => _state;

  // Stubs for methods not used in social accounts tests.
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Helper: build widget under test
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required ProfileState profileState,
}) {
  final notifier = _FakeProfileNotifier(profileState);

  return ProviderScope(
    overrides: [
      profileProvider.overrideWith(() => notifier),
    ],
    child: const MaterialApp(
      home: SocialAccountsScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('SocialAccountsScreen', () {
    testWidgets('shows Link button when provider is not linked', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileNotLinked),
        ),
      );
      await tester.pumpAndSettle();

      // Verify screen title
      expect(find.text('Social Accounts'), findsOneWidget);

      // Verify header description
      expect(
        find.text(
          'Link your social accounts for easier sign-in and account recovery.',
        ),
        findsOneWidget,
      );

      // Verify Telegram provider shows "Not Linked" status
      expect(find.text('Telegram'), findsOneWidget);
      expect(find.text('Not Linked'), findsAtLeastNWidgets(1));

      // Verify Link button is present for Telegram
      expect(
        find.widgetWithText(FilledButton, 'Link'),
        findsAtLeastNWidgets(1),
      );

      // Verify GitHub provider is also shown
      expect(find.text('GitHub'), findsOneWidget);
    });

    testWidgets('shows Unlink button and username when provider is linked',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileLinked),
        ),
      );
      await tester.pumpAndSettle();

      // Verify screen title
      expect(find.text('Social Accounts'), findsOneWidget);

      // Verify Telegram provider shows "Linked" status
      expect(find.text('Telegram'), findsOneWidget);
      expect(find.text('Linked'), findsOneWidget);

      // Verify Telegram username is displayed
      expect(find.text('@telegram_user'), findsOneWidget);

      // Verify Unlink button is present for Telegram
      expect(
        find.widgetWithText(OutlinedButton, 'Unlink'),
        findsOneWidget,
      );
    });

    testWidgets('shows confirmation dialog when Unlink button is tapped',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileLinked),
        ),
      );
      await tester.pumpAndSettle();

      // Tap the Unlink button
      await tester.tap(find.widgetWithText(OutlinedButton, 'Unlink'));
      await tester.pumpAndSettle();

      // Verify confirmation dialog appears
      expect(find.text('Unlink Telegram?'), findsOneWidget);
      expect(
        find.text(
          'You will need to re-authorize to link this account again. '
          'This will not delete your Telegram account.',
        ),
        findsOneWidget,
      );

      // Verify dialog buttons
      expect(find.widgetWithText(TextButton, 'Cancel'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Unlink'), findsOneWidget);
    });

    testWidgets('closes dialog when Cancel button is tapped', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileLinked),
        ),
      );
      await tester.pumpAndSettle();

      // Tap the Unlink button to show dialog
      await tester.tap(find.widgetWithText(OutlinedButton, 'Unlink'));
      await tester.pumpAndSettle();

      // Tap Cancel button
      await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
      await tester.pumpAndSettle();

      // Verify dialog is dismissed
      expect(find.text('Unlink Telegram?'), findsNothing);
    });
  });
}
