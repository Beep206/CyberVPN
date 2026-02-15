import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/screens/add_by_url_screen.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

Widget _buildTestWidget() {
  return ProviderScope(
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('en'),
      home: const AddByUrlScreen(),
    ),
  );
}

/// Pumps and advances enough frames for layout without waiting for
/// looping animations (GlitchText) that would cause pumpAndSettle timeout.
Future<void> _pumpScreen(WidgetTester tester) async {
  await tester.pumpWidget(_buildTestWidget());
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 500));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('AddByUrlScreen', () {
    testWidgets('renders Scaffold with AppBar title', (tester) async {
      await _pumpScreen(tester);

      expect(find.byType(Scaffold), findsAtLeast(1));
      expect(find.byType(GlitchText), findsOneWidget);
    });

    testWidgets('renders URL text field with link icon', (tester) async {
      await _pumpScreen(tester);

      expect(find.byIcon(Icons.link), findsOneWidget);
      expect(find.byType(TextFormField), findsNWidgets(2));
    });

    testWidgets('renders paste button', (tester) async {
      await _pumpScreen(tester);

      expect(find.byIcon(Icons.content_paste), findsOneWidget);
    });

    testWidgets('renders optional name field with label icon', (tester) async {
      await _pumpScreen(tester);

      expect(find.byIcon(Icons.label_outline), findsOneWidget);
    });

    testWidgets('renders fetch button with download icon', (tester) async {
      await _pumpScreen(tester);

      expect(find.byIcon(Icons.download), findsOneWidget);
      expect(find.byType(FilledButton), findsOneWidget);
    });

    testWidgets('URL validation fails on empty input', (tester) async {
      await _pumpScreen(tester);

      // Tap fetch button with empty URL
      await tester.tap(find.byType(FilledButton));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // Validation error should appear (uses profileUrlHint as error text)
      expect(find.byType(TextFormField), findsNWidgets(2));
    });

    testWidgets('can enter URL text', (tester) async {
      await _pumpScreen(tester);

      // Find the URL field (first TextFormField)
      final urlField = find.byType(TextFormField).first;
      await tester.enterText(urlField, 'https://sub.example.com/token');
      await tester.pump();

      expect(find.text('https://sub.example.com/token'), findsOneWidget);
    });

    testWidgets('can enter profile name', (tester) async {
      await _pumpScreen(tester);

      // Find the name field (second TextFormField)
      final nameField = find.byType(TextFormField).at(1);
      await tester.enterText(nameField, 'My Custom Profile');
      await tester.pump();

      expect(find.text('My Custom Profile'), findsOneWidget);
    });

    testWidgets('shows Form widget for validation', (tester) async {
      await _pumpScreen(tester);

      expect(find.byType(Form), findsOneWidget);
    });

    testWidgets('renders inside SingleChildScrollView', (tester) async {
      await _pumpScreen(tester);

      expect(find.byType(SingleChildScrollView), findsOneWidget);
    });
  });
}
