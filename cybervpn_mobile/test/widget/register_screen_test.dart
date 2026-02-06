import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/presentation/screens/register_screen.dart';

import '../helpers/mock_repositories.dart';
import 'auth_test_helpers.dart';

void main() {
  late MockAuthRepository mockAuthRepo;

  setUp(() {
    mockAuthRepo = MockAuthRepository();
    stubUnauthenticated(mockAuthRepo);
  });

  Widget buildSubject() {
    return buildTestableAuthScreen(
      child: const RegisterScreen(),
      path: '/register',
      overrides: authOverrides(mockAuthRepo),
    );
  }

  /// Settles the widget tree without waiting for animations that never end
  /// (e.g. the LinearProgressIndicator in the password strength indicator).
  /// Use this instead of [pumpAndSettle] after entering text in password fields.
  Future<void> pumpFrames(WidgetTester tester, {int count = 5}) async {
    for (var i = 0; i < count; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  group('RegisterScreen', () {
    testWidgets('renders branding elements', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Create Account'), findsOneWidget);
      expect(
          find.text('Join CyberVPN for a secure experience'), findsOneWidget);
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
    });

    testWidgets('renders all form fields', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(findEmailField(), findsOneWidget);
      expect(findPasswordField(), findsOneWidget);
      expect(findConfirmPasswordField(), findsOneWidget);
      expect(
          find.widgetWithText(TextFormField, 'Referral Code (optional)'),
          findsOneWidget);
    });

    testWidgets('renders Register button', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(findRegisterButton(), findsOneWidget);
    });

    testWidgets('renders login link', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Already have an account? '), findsOneWidget);
      expect(find.text('Login'), findsOneWidget);
    });

    testWidgets('renders Terms & Conditions checkbox', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.byType(Checkbox), findsOneWidget);
      expect(
        find.byWidgetPredicate(
          (widget) =>
              widget is RichText &&
              widget.text.toPlainText().contains('I agree to the'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('renders social login button', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Continue with Telegram'), findsOneWidget);
    });

    group('form validation', () {
      testWidgets('empty email shows validation error on submit',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.tap(findRegisterButton());
        await tester.pumpAndSettle();

        expect(find.text('Email is required'), findsOneWidget);
      });

      testWidgets('empty password shows validation error on submit',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.tap(findRegisterButton());
        await tester.pumpAndSettle();

        expect(find.text('Password is required'), findsOneWidget);
      });

      testWidgets('invalid email shows validation error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), 'bad-email');
        await tester.tap(findRegisterButton());
        await tester.pumpAndSettle();

        expect(
            find.text('Please enter a valid email address'), findsOneWidget);
      });

      testWidgets('password mismatch shows error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();
        await tester.enterText(findConfirmPasswordField(), 'DifferentPass1');
        await tester.pump();

        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester);

        expect(find.text('Passwords do not match'), findsOneWidget);
      });

      testWidgets('empty confirm password shows error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();

        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester);

        expect(find.text('Please confirm your password'), findsOneWidget);
      });

      testWidgets('short password shows validation error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), 'Ab1');
        await tester.pump();

        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester);

        expect(find.text('Password must be at least 8 characters'),
            findsOneWidget);
      });
    });

    group('terms and conditions', () {
      testWidgets(
          'submit without accepting terms shows SnackBar warning',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.pump();
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();
        await tester.enterText(findConfirmPasswordField(), kValidPassword);
        await tester.pump();

        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester);

        expect(find.text('Please accept the Terms & Conditions'),
            findsOneWidget);
      });
    });

    group('successful registration', () {
      testWidgets('valid form calls auth provider register', (tester) async {
        ignoreOverflowErrors();
        stubRegisterSuccess(mockAuthRepo);

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.pump();
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();
        await tester.enterText(findConfirmPasswordField(), kValidPassword);
        await tester.pump();

        // Accept T&C
        await tester.ensureVisible(find.byType(Checkbox));
        await tester.pump();
        await tester.tap(find.byType(Checkbox));
        await pumpFrames(tester);

        // Submit
        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester, count: 10);

        verify(() => mockAuthRepo.register(
              email: kValidEmail,
              password: kValidPassword,
              device: any(named: 'device'),
              referralCode: null,
            )).called(1);
      });

      testWidgets('navigates to /connection on success', (tester) async {
        ignoreOverflowErrors();
        stubRegisterSuccess(mockAuthRepo);

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.pump();
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();
        await tester.enterText(findConfirmPasswordField(), kValidPassword);
        await tester.pump();

        await tester.ensureVisible(find.byType(Checkbox));
        await tester.pump();
        await tester.tap(find.byType(Checkbox));
        await pumpFrames(tester);

        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester, count: 10);

        expect(find.text('Connection Screen'), findsOneWidget);
      });
    });

    group('failed registration', () {
      testWidgets('API error shows error message in SnackBar',
          (tester) async {
        ignoreOverflowErrors();
        stubRegisterFailure(mockAuthRepo, message: 'Email already taken');

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.pump();
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();
        await tester.enterText(findConfirmPasswordField(), kValidPassword);
        await tester.pump();

        await tester.ensureVisible(find.byType(Checkbox));
        await tester.pump();
        await tester.tap(find.byType(Checkbox));
        await pumpFrames(tester);

        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester, count: 10);

        expect(find.byType(SnackBar), findsOneWidget);
      });
    });

    group('password visibility toggle', () {
      testWidgets('password field starts obscured', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        expect(find.byIcon(Icons.visibility_outlined), findsNWidgets(2));
      });

      testWidgets('tapping visibility icon toggles obscureText',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        final visibilityIcons = find.byIcon(Icons.visibility_outlined);
        await tester.tap(visibilityIcons.first);
        await tester.pumpAndSettle();

        expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);
      });
    });

    group('navigation', () {
      testWidgets('tapping Login link navigates to /login', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        final loginLink = find.text('Login');
        await tester.ensureVisible(loginLink);
        await tester.pumpAndSettle();
        await tester.tap(loginLink);
        await tester.pumpAndSettle();

        expect(find.text('Login Screen Route'), findsOneWidget);
      });
    });

    group('referral code field', () {
      testWidgets('is visible when referral system is available',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        expect(
            find.widgetWithText(TextFormField, 'Referral Code (optional)'),
            findsOneWidget);
      });

      testWidgets('is hidden when referral system is unavailable',
          (tester) async {
        ignoreOverflowErrors();
        final widget = buildTestableAuthScreen(
          child: const RegisterScreen(),
          path: '/register',
          overrides: authOverrides(mockAuthRepo, referralAvailable: false),
        );
        await tester.pumpWidget(widget);
        await tester.pumpAndSettle();

        expect(
            find.widgetWithText(TextFormField, 'Referral Code (optional)'),
            findsNothing);
      });

      testWidgets('shows Applied! chip when valid code is entered',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        final referralField =
            find.widgetWithText(TextFormField, 'Referral Code (optional)');
        await tester.ensureVisible(referralField);
        await tester.pump();

        // Enter a valid referral code
        await tester.enterText(referralField, 'TESTCODE123');
        await pumpFrames(tester);

        // Check for Applied! chip
        expect(find.text('Applied!'), findsOneWidget);
        expect(find.byType(Chip), findsOneWidget);
      });

      testWidgets('does not show Applied! chip for invalid code',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        final referralField =
            find.widgetWithText(TextFormField, 'Referral Code (optional)');
        await tester.ensureVisible(referralField);
        await tester.pump();

        // Enter an invalid referral code (too short)
        await tester.enterText(referralField, 'ABC');
        await pumpFrames(tester);

        // Applied! chip should not appear
        expect(find.text('Applied!'), findsNothing);
      });

      testWidgets('includes referral code in registration call',
          (tester) async {
        ignoreOverflowErrors();
        stubRegisterSuccess(mockAuthRepo);

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.pump();
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.pump();
        await tester.enterText(findConfirmPasswordField(), kValidPassword);
        await tester.pump();

        // Enter referral code
        final referralField =
            find.widgetWithText(TextFormField, 'Referral Code (optional)');
        await tester.ensureVisible(referralField);
        await tester.pump();
        await tester.enterText(referralField, 'MYCODE2024');
        await pumpFrames(tester);

        // Accept T&C
        await tester.ensureVisible(find.byType(Checkbox));
        await tester.pump();
        await tester.tap(find.byType(Checkbox));
        await pumpFrames(tester);

        // Submit
        await tester.ensureVisible(findRegisterButton());
        await tester.pump();
        await tester.tap(findRegisterButton());
        await pumpFrames(tester, count: 10);

        // Verify the referral code was passed
        verify(() => mockAuthRepo.register(
              email: kValidEmail,
              password: kValidPassword,
              device: any(named: 'device'),
              referralCode: 'MYCODE2024',
            )).called(1);
      });
    });
  });
}
