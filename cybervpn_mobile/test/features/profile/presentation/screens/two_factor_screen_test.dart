import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/two_factor_screen.dart';

void main() {
  /// Helper to build the screen with necessary providers
  Widget buildScreen({
    required ProfileState initialState,
    TestProfileNotifier? notifier,
  }) {
    return ProviderScope(
      overrides: [
        profileProvider.overrideWith(() {
          return notifier ?? TestProfileNotifier(initialState);
        }),
      ],
      child: const MaterialApp(
        home: TwoFactorScreen(),
      ),
    );
  }

  group('TwoFactorScreen - Not Enabled State', () {
    testWidgets('displays not enabled UI with Enable button',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      // Act
      await tester.pumpWidget(buildScreen(initialState: profileState));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('2FA Disabled'), findsOneWidget);
      expect(find.text('Enable 2FA to secure your account'), findsOneWidget);
      expect(find.text('Enable 2FA'), findsOneWidget);
      expect(
        find.text('What is Two-Factor Authentication?'),
        findsOneWidget,
      );
    });

    testWidgets('calls setup2FA when Enable button is tapped',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      // Tap Enable button
      await tester.tap(find.text('Enable 2FA'));
      await tester.pumpAndSettle();

      // Assert
      expect(notifier.setup2FACalled, isTrue);
    });
  });

  group('TwoFactorScreen - Setup State', () {
    testWidgets('displays QR code and code input after enabling',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      // Tap Enable button
      await tester.tap(find.text('Enable 2FA'));
      await tester.pumpAndSettle();

      // Assert - QR code section
      expect(find.text('Step 1: Scan QR Code'), findsOneWidget);
      expect(
        find.text('Scan this QR code with your authenticator app'),
        findsOneWidget,
      );

      // Assert - Verification section
      expect(find.text('Step 2: Verify Code'), findsOneWidget);
      expect(
        find.text('Enter the 6-digit code from your authenticator app'),
        findsOneWidget,
      );
      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('Verify and Enable'), findsOneWidget);
    });

    testWidgets('verify button is disabled until 6-digit code is entered',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Enable 2FA'));
      await tester.pumpAndSettle();

      // Assert - button disabled initially
      final verifyButton =
          find.widgetWithText(FilledButton, 'Verify and Enable');
      expect(tester.widget<FilledButton>(verifyButton).onPressed, isNull);

      // Enter partial code
      await tester.enterText(find.byType(TextField), '12345');
      await tester.pump();

      // Assert - still disabled
      expect(tester.widget<FilledButton>(verifyButton).onPressed, isNull);

      // Enter full 6-digit code
      await tester.enterText(find.byType(TextField), '123456');
      await tester.pump();

      // Assert - now enabled
      expect(tester.widget<FilledButton>(verifyButton).onPressed, isNotNull);
    });

    testWidgets('calls verify2FA with entered code when Verify is tapped',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Enable 2FA'));
      await tester.pumpAndSettle();

      // Enter code
      await tester.enterText(find.byType(TextField), '123456');
      await tester.pump();

      // Tap verify (skip scrolling for this test as the button might be partially visible)
      await tester.tap(find.text('Verify and Enable'));
      await tester.pumpAndSettle();

      // Assert
      expect(notifier.verify2FACalled, isTrue);
      expect(notifier.lastVerifyCode, '123456');
    });

    testWidgets('shows backup codes dialog after successful verification',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Enable 2FA'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '123456');
      await tester.pump();

      await tester.tap(find.text('Verify and Enable'));
      await tester.pumpAndSettle();

      // Assert - backup codes dialog shown
      expect(find.text('Backup Codes'), findsOneWidget);
      expect(
        find.text(
          'Save these backup codes in a safe place. Each code can '
          'only be used once to sign in if you lose access to your '
          'authenticator app.',
        ),
        findsOneWidget,
      );
      expect(find.text('Copy All'), findsOneWidget);
    });

    testWidgets('cancel button returns to not enabled state',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: false,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Enable 2FA'));
      await tester.pumpAndSettle();

      // Tap cancel
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      // Assert - back to not enabled state
      expect(find.text('Enable 2FA'), findsOneWidget);
      expect(find.text('What is Two-Factor Authentication?'), findsOneWidget);
    });
  });

  group('TwoFactorScreen - Enabled State', () {
    testWidgets('displays enabled UI with Disable button',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: true,
        ),
      );

      // Act
      await tester.pumpWidget(buildScreen(initialState: profileState));
      await tester.pumpAndSettle();

      // Assert
      expect(find.text('2FA Enabled'), findsOneWidget);
      expect(
        find.text('Your account is protected with two-factor authentication'),
        findsOneWidget,
      );
      expect(
        find.text('Two-Factor Authentication is Active'),
        findsOneWidget,
      );
      expect(find.text('Disable 2FA'), findsOneWidget);
    });

    testWidgets('shows confirmation dialog when Disable is tapped',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: true,
        ),
      );

      // Act
      await tester.pumpWidget(buildScreen(initialState: profileState));
      await tester.pumpAndSettle();

      // Tap Disable button
      await tester.tap(find.text('Disable 2FA'));
      await tester.pumpAndSettle();

      // Assert - confirmation dialog shown
      expect(
        find.text('Disable Two-Factor Authentication?'),
        findsOneWidget,
      );
      expect(
        find.text(
          'Disabling 2FA will make your account less secure. '
          'You\'ll only need your password to sign in.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows code input dialog after confirming disable',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: true,
        ),
      );

      // Act
      await tester.pumpWidget(buildScreen(initialState: profileState));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Disable 2FA'));
      await tester.pumpAndSettle();

      // Confirm disable
      await tester.tap(find.widgetWithText(FilledButton, 'Disable'));
      await tester.pumpAndSettle();

      // Assert - code input dialog shown
      expect(find.text('Enter Verification Code'), findsOneWidget);
      expect(
        find.text('Enter the 6-digit code from your authenticator app'),
        findsOneWidget,
      );
    });

    testWidgets('calls disable2FA with code when confirmed',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: true,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Disable 2FA'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Disable'));
      await tester.pumpAndSettle();

      // Enter code in dialog
      await tester.enterText(find.byType(TextField), '654321');
      await tester.pump();

      // Confirm
      await tester.tap(find.widgetWithText(FilledButton, 'Confirm'));
      await tester.pumpAndSettle();

      // Assert
      expect(notifier.disable2FACalled, isTrue);
      expect(notifier.lastDisableCode, '654321');
    });

    testWidgets('transitions to not enabled state after successful disable',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: true,
        ),
      );

      final notifier = TestProfileNotifier(profileState);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      // Scroll to Disable button and tap
      await tester.ensureVisible(find.text('Disable 2FA'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Disable 2FA'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Disable'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '654321');
      await tester.pump();

      await tester.tap(find.widgetWithText(FilledButton, 'Confirm'));
      await tester.pumpAndSettle();

      // Assert - back to not enabled state
      expect(find.text('2FA Disabled'), findsOneWidget);
      expect(find.text('Enable 2FA'), findsOneWidget);
    });

    testWidgets('shows error snackbar on disable failure',
        (WidgetTester tester) async {
      // Arrange
      const profileState = ProfileState(
        profile: Profile(
          id: '1',
          email: 'test@example.com',
          is2FAEnabled: true,
        ),
      );

      final notifier = TestProfileNotifier(profileState, shouldFailDisable: true);

      // Act
      await tester.pumpWidget(buildScreen(
        initialState: profileState,
        notifier: notifier,
      ));
      await tester.pumpAndSettle();

      // Scroll to Disable button and tap
      await tester.ensureVisible(find.text('Disable 2FA'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Disable 2FA'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Disable'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '654321');
      await tester.pump();

      await tester.tap(find.widgetWithText(FilledButton, 'Confirm'));
      await tester.pumpAndSettle();

      // Assert - error message shown
      expect(find.textContaining('Failed to disable 2FA'), findsOneWidget);

      // State should still be enabled
      expect(find.text('2FA Enabled'), findsOneWidget);
    });
  });
}

// ---------------------------------------------------------------------------
// Test Notifier
// ---------------------------------------------------------------------------

/// Test implementation of ProfileNotifier for widget testing
class TestProfileNotifier extends ProfileNotifier {
  TestProfileNotifier(
    this._initialState, {
    this.shouldFailDisable = false,
  });

  final ProfileState _initialState;
  final bool shouldFailDisable;

  bool setup2FACalled = false;
  bool verify2FACalled = false;
  bool disable2FACalled = false;
  String? lastVerifyCode;
  String? lastDisableCode;

  @override
  Future<ProfileState> build() async {
    return _initialState;
  }

  @override
  Future<Setup2FAResult> setup2FA() async {
    setup2FACalled = true;
    return const Setup2FAResult(
      secret: 'TESTSECRET123456',
      qrCodeUri:
          'otpauth://totp/CyberVPN:test@example.com?secret=TESTSECRET123456&issuer=CyberVPN',
    );
  }

  @override
  Future<bool> verify2FA(String code) async {
    verify2FACalled = true;
    lastVerifyCode = code;
    return true;
  }

  @override
  Future<void> disable2FA(String code) async {
    disable2FACalled = true;
    lastDisableCode = code;
    if (shouldFailDisable) {
      throw Exception('Invalid code');
    }
  }
}
