import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show profileRepositoryProvider;
import 'package:cybervpn_mobile/features/profile/presentation/screens/delete_account_screen.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

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
  createdAt: DateTime(2024, 1, 1),
  lastLoginAt: DateTime(2025, 12, 1),
);

final _testProfile2FA = Profile(
  id: 'user-2',
  email: 'test2fa@example.com',
  username: 'Test User 2FA',
  isEmailVerified: true,
  is2FAEnabled: true,
  linkedProviders: [],
  createdAt: DateTime(2024, 1, 1),
  lastLoginAt: DateTime(2025, 12, 1),
);

// ---------------------------------------------------------------------------
// Mock profile repository
// ---------------------------------------------------------------------------

class _MockProfileRepository implements ProfileRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
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
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Helper: build widget under test
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required ProfileState profileState,
}) {
  final fakeProfileNotifier = _FakeProfileNotifier(profileState);

  return ProviderScope(
    overrides: [
      profileProvider.overrideWith(() => fakeProfileNotifier),
      profileRepositoryProvider.overrideWithValue(_MockProfileRepository()),
      vpnConnectionProvider.overrideWith(
        () => _FakeVpnConnectionNotifier(const VpnDisconnected()),
      ),
    ],
    child: const MaterialApp(
      home: DeleteAccountScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Fake VPN connection notifier
// ---------------------------------------------------------------------------

class _FakeVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _FakeVpnConnectionNotifier(this._state);

  final VpnConnectionState _state;

  @override
  Future<VpnConnectionState> build() async => _state;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('DeleteAccountScreen', () {
    testWidgets('renders warning step on initial load', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Verify warning header is displayed
      expect(find.text('Danger Zone'), findsOneWidget);
      expect(find.text('This action cannot be undone'), findsOneWidget);

      // Verify data deletion list
      expect(find.text('What will be deleted?'), findsOneWidget);
      expect(find.text('Personal Information'), findsOneWidget);
      expect(find.text('Subscription & Payment History'), findsOneWidget);
      expect(find.text('VPN Configurations'), findsOneWidget);
      expect(find.text('App Settings'), findsOneWidget);

      // Verify grace period notice
      expect(find.text('30-Day Grace Period'), findsOneWidget);

      // Verify action buttons
      expect(find.text('Continue with Deletion'), findsOneWidget);
      expect(find.text('Cancel'), findsOneWidget);
    });

    testWidgets('navigates to re-authentication step on continue',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Tap continue button
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();

      // Verify re-authentication step is displayed
      expect(find.text('Verify Your Identity'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(
        find.text(
          'For security reasons, please re-enter your credentials to confirm '
          'account deletion.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows TOTP field when 2FA is enabled', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile2FA),
        ),
      );
      await tester.pumpAndSettle();

      // Navigate to re-authentication step
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();

      // Verify TOTP field is displayed
      expect(find.text('Verify Your Identity'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('6-digit code'), findsOneWidget);
      expect(
        find.text('Enter the 6-digit code from your authenticator app'),
        findsOneWidget,
      );
    });

    testWidgets('does not show TOTP field when 2FA is disabled',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Navigate to re-authentication step
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();

      // Verify TOTP field is NOT displayed
      expect(find.text('Verify Your Identity'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('6-digit code'), findsNothing);
    });

    testWidgets('navigates back to warning step from re-authentication',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Navigate to re-authentication step
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();

      expect(find.text('Verify Your Identity'), findsOneWidget);

      // Tap back button
      final backButtons = find.text('Back');
      await tester.tap(backButtons.first);
      await tester.pumpAndSettle();

      // Verify we're back at warning step
      expect(find.text('What will be deleted?'), findsOneWidget);
    });

    testWidgets('navigates to final confirmation after re-auth',
        (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Navigate to re-authentication step
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();

      // Enter password
      await tester.enterText(find.byType(TextField).first, 'password123');
      await tester.pumpAndSettle();

      // Tap verify and continue
      await tester.tap(find.text('Verify and Continue'));
      await tester.pumpAndSettle();

      // Verify final confirmation step is displayed
      expect(find.text('Final Confirmation'), findsOneWidget);
      expect(find.text('Type DELETE to confirm'), findsOneWidget);
      expect(
        find.text('This is your last chance to cancel. Once confirmed, your account '
            'will be scheduled for permanent deletion.'),
        findsOneWidget,
      );
    });

    testWidgets('requires DELETE confirmation text', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Navigate to final confirmation
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).first, 'password123');
      await tester.pumpAndSettle();
      await tester.tap(find.text('Verify and Continue'));
      await tester.pumpAndSettle();

      // Verify delete button is disabled initially
      final deleteButton =
          tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Delete My Account'));
      expect(deleteButton.onPressed, isNull);

      // Enter DELETE
      await tester.enterText(find.byType(TextField).last, 'DELETE');
      await tester.pumpAndSettle();

      // Verify delete button is now enabled
      final enabledButton =
          tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Delete My Account'));
      expect(enabledButton.onPressed, isNotNull);
    });

    testWidgets('password visibility toggle works', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profileState: ProfileState(profile: _testProfile),
        ),
      );
      await tester.pumpAndSettle();

      // Navigate to re-authentication step
      await tester.tap(find.text('Continue with Deletion'));
      await tester.pumpAndSettle();

      // Find password field
      final passwordField = tester.widget<TextField>(find.byType(TextField).first);
      expect(passwordField.obscureText, isTrue);

      // Tap visibility toggle
      await tester.tap(find.byIcon(Icons.visibility));
      await tester.pumpAndSettle();

      // Verify password is now visible
      final visiblePasswordField =
          tester.widget<TextField>(find.byType(TextField).first);
      expect(visiblePasswordField.obscureText, isFalse);
    });
  });
}
