import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
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
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('en'),
      home: const SocialAccountsScreen(),
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

    testWidgets('Telegram card is highlighted with neon cyan border',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileNotLinked),
        ),
      );
      await tester.pumpAndSettle();

      // Find the Telegram provider card by its key
      final telegramCard = find.byKey(const Key('provider_telegram'));
      expect(telegramCard, findsOneWidget);

      // Find the Card widget inside the Telegram provider card
      final cardFinder = find.descendant(
        of: telegramCard,
        matching: find.byType(Card),
      );
      expect(cardFinder, findsOneWidget);

      final cardWidget = tester.widget<Card>(cardFinder);
      // Highlighted card should have a custom shape with border
      expect(cardWidget.shape, isA<RoundedRectangleBorder>());
      final shape = cardWidget.shape as RoundedRectangleBorder;
      expect(shape.side.width, 1.5);
    });

    testWidgets('disables Unlink when Telegram is only login method (no email)',
        (tester) async {
      final telegramOnlyProfile = Profile(
        id: 'user-1',
        email: '',
        username: 'testuser',
        isEmailVerified: false,
        is2FAEnabled: false,
        linkedProviders: [OAuthProvider.telegram],
        createdAt: DateTime(2024, 1, 1),
      );

      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: telegramOnlyProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Unlink button exists but is disabled
      final unlinkButton = find.byKey(const Key('unlink_telegram'));
      expect(unlinkButton, findsOneWidget);

      final button = tester.widget<OutlinedButton>(unlinkButton);
      expect(button.onPressed, isNull);

      // Verify warning message is shown
      expect(
        find.text('Cannot unlink — this is your only login method'),
        findsOneWidget,
      );
    });

    testWidgets('enables Unlink when email is verified (alternative login)',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileLinked),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Unlink button exists and is enabled
      final unlinkButton = find.byKey(const Key('unlink_telegram'));
      expect(unlinkButton, findsOneWidget);

      final button = tester.widget<OutlinedButton>(unlinkButton);
      expect(button.onPressed, isNotNull);

      // No warning message
      expect(
        find.text('Cannot unlink — this is your only login method'),
        findsNothing,
      );
    });

    testWidgets('enables Unlink when other providers are linked',
        (tester) async {
      final multiProviderProfile = Profile(
        id: 'user-1',
        email: '',
        username: 'testuser',
        isEmailVerified: false,
        is2FAEnabled: false,
        linkedProviders: [OAuthProvider.telegram, OAuthProvider.github],
        createdAt: DateTime(2024, 1, 1),
      );

      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: multiProviderProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Unlink button for Telegram is enabled
      final unlinkButton = find.byKey(const Key('unlink_telegram'));
      expect(unlinkButton, findsOneWidget);

      final button = tester.widget<OutlinedButton>(unlinkButton);
      expect(button.onPressed, isNotNull);
    });

    testWidgets('Telegram and GitHub provider cards are visible at top',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfileNotLinked),
        ),
      );
      await tester.pumpAndSettle();

      // First providers should be visible without scrolling
      expect(find.text('Telegram'), findsOneWidget);
      expect(find.text('GitHub'), findsOneWidget);
      expect(find.text('Google'), findsOneWidget);
    });
  });
}
