import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/presentation/screens/login_screen.dart';
import 'package:cybervpn_mobile/features/auth/presentation/widgets/login_form.dart';

import '../../../../helpers/mock_repositories.dart';
import '../../../../helpers/auth_test_helpers.dart';

void main() {
  late MockAuthRepository mockAuthRepo;

  setUp(() {
    mockAuthRepo = MockAuthRepository();
    stubUnauthenticated(mockAuthRepo);
  });

  Widget buildSubject() {
    return buildTestableAuthScreen(
      child: const LoginScreen(),
      path: '/login',
      overrides: authOverrides(mockAuthRepo),
    );
  }

  group('LoginScreen', () {
    testWidgets('renders branding elements', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('CyberVPN'), findsOneWidget);
      expect(find.text('Secure your connection'), findsOneWidget);
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
    });

    testWidgets('renders the LoginForm widget', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.byType(LoginForm), findsOneWidget);
    });

    testWidgets('renders email and password fields', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(findEmailField(), findsOneWidget);
      expect(findPasswordField(), findsOneWidget);
    });

    testWidgets('renders Login button', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(findLoginButton(), findsOneWidget);
    });

    testWidgets('renders register link', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text("Don't have an account? "), findsOneWidget);
      expect(find.text('Register'), findsOneWidget);
    });

    testWidgets('renders social login button', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Continue with Telegram'), findsOneWidget);
    });

    group('form validation', () {
      testWidgets('empty email shows validation error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        expect(find.text('Email is required'), findsOneWidget);
      });

      testWidgets('empty password shows validation error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        expect(find.text('Password is required'), findsOneWidget);
      });

      testWidgets('invalid email shows validation error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), 'not-an-email');
        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        expect(
            find.text('Please enter a valid email address'), findsOneWidget);
      });

      testWidgets('short password shows validation error', (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), 'Ab1');
        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        expect(find.text('Password must be at least 8 characters'),
            findsOneWidget);
      });
    });

    group('successful login', () {
      testWidgets('valid form calls auth provider login', (tester) async {
        ignoreOverflowErrors();
        stubLoginSuccess(mockAuthRepo);

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        verify(() => mockAuthRepo.login(
              email: kValidEmail,
              password: kValidPassword,
              device: any(named: 'device'),
            )).called(1);
      });

      testWidgets('navigates to /connection on success', (tester) async {
        ignoreOverflowErrors();
        stubLoginSuccess(mockAuthRepo);

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        expect(find.text('Connection Screen'), findsOneWidget);
      });
    });

    group('failed login', () {
      testWidgets('API error shows error message in SnackBar',
          (tester) async {
        ignoreOverflowErrors();
        stubLoginFailure(mockAuthRepo, message: 'Invalid credentials');

        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        await tester.enterText(findEmailField(), kValidEmail);
        await tester.enterText(findPasswordField(), kValidPassword);
        await tester.tap(findLoginButton());
        await tester.pumpAndSettle();

        expect(find.byType(SnackBar), findsOneWidget);
      });
    });

    group('navigation', () {
      testWidgets('tapping Register link navigates to /register',
          (tester) async {
        ignoreOverflowErrors();
        await tester.pumpWidget(buildSubject());
        await tester.pumpAndSettle();

        final registerLink = find.text('Register');
        await tester.ensureVisible(registerLink);
        await tester.pumpAndSettle();
        await tester.tap(registerLink);
        await tester.pumpAndSettle();

        expect(find.text('Register Screen Route'), findsOneWidget);
      });
    });
  });
}
