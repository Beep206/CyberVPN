import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/magic_link_screen.dart';

void main() {
  /// Builds the [MagicLinkScreen] inside a fully wired widget tree that
  /// provides Riverpod, GoRouter, and localization delegates.
  ///
  /// The GoRouter has placeholder routes for /magic-link and /login so that
  /// navigation calls (context.go) do not throw during tests.
  Widget buildSubject() {
    final router = GoRouter(
      initialLocation: '/magic-link',
      routes: [
        GoRoute(
          path: '/magic-link',
          builder: (_, __) => const MagicLinkScreen(),
        ),
        GoRoute(
          path: '/login',
          builder: (_, __) =>
              const Scaffold(body: Text('Login Screen Route')),
        ),
      ],
    );

    return ProviderScope(
      child: MaterialApp.router(
        routerConfig: router,
        theme: ThemeData.light(useMaterial3: true),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('en'),
      ),
    );
  }

  /// Suppresses RenderFlex overflow errors that can occur in the constrained
  /// test viewport. This keeps tests focused on behavior rather than layout.
  void ignoreOverflowErrors() {
    FlutterError.onError = (details) {
      final isOverflow = details.toString().contains('overflowed');
      if (!isOverflow) {
        FlutterError.dumpErrorToConsole(details);
        throw details.exception;
      }
    };
  }

  group('MagicLinkScreen — initial state', () {
    testWidgets('renders title text', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      // The title "Magic Link Login" appears in both the AppBar and the body
      expect(find.text('Magic Link Login'), findsAtLeast(1));
    });

    testWidgets('renders email input field', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      // The email field has a hint text and label
      expect(find.text('Email'), findsOneWidget);
    });

    testWidgets('renders send button', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Send Magic Link'), findsOneWidget);
      expect(find.byType(FilledButton), findsOneWidget);
    });

    testWidgets('renders subtitle text', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Enter your email and we will send you a single-use login link. No password needed.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('renders Back to Login link', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Back to Login'), findsOneWidget);
      expect(find.byType(TextButton), findsOneWidget);
    });

    testWidgets('renders mail icon', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.mail_outline), findsOneWidget);
    });

    testWidgets('email field validates empty input', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      // Tap the send button without entering an email
      await tester.tap(find.text('Send Magic Link'));
      await tester.pumpAndSettle();

      // The form validator should show "This field is required."
      expect(find.text('This field is required.'), findsOneWidget);
    });

    testWidgets('email field validates input without @ symbol',
        (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      // Enter an invalid email (no @)
      await tester.enterText(find.byType(TextFormField), 'invalidemail');
      await tester.tap(find.text('Send Magic Link'));
      await tester.pumpAndSettle();

      expect(
        find.text('Please enter a valid email address.'),
        findsOneWidget,
      );
    });
  });
}
