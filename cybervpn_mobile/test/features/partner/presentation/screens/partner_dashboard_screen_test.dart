import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/partner/presentation/providers/partner_provider.dart';
import 'package:cybervpn_mobile/features/partner/presentation/screens/partner_dashboard_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockPartnerRepository extends Mock {}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestablePartnerDashboard({
  bool isPartner = true,
  Map<String, dynamic>? dashboardData,
  List<Map<String, dynamic>>? codes,
  List<Map<String, dynamic>>? earnings,
}) {
  final mockRepo = MockPartnerRepository();

  if (isPartner) {
    when(() => mockRepo.getDashboard()).thenAnswer(
      (_) async => Success(
        data: dashboardData ??
            {
              'total_earnings': 500.0,
              'active_codes': 5,
              'referrals': 20,
            },
      ),
    );

    when(() => mockRepo.getCodes()).thenAnswer(
      (_) async => Success(
        data: codes ??
            [
              {
                'code': 'PARTNER2024',
                'markup_percent': 15,
                'uses_count': 10,
                'earnings': 150.0,
              },
            ],
      ),
    );

    when(() => mockRepo.getEarnings()).thenAnswer(
      (_) async => Success(
        data: earnings ??
            [
              {
                'date': '2026-02-11',
                'code': 'PARTNER2024',
                'amount': 25.0,
              },
            ],
      ),
    );
  } else {
    when(() => mockRepo.getDashboard()).thenAnswer(
      (_) async => Failure(failure: Exception('Not a partner')),
    );
  }

  when(() => mockRepo.bindPartnerCode(any())).thenAnswer(
    (_) async => const Success(data: {}),
  );

  return ProviderScope(
    overrides: [
      partnerRepositoryProvider.overrideWithValue(mockRepo),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: PartnerDashboardScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('PartnerDashboardScreen - Partner View', () {
    testWidgets('test_renders_partner_dashboard_title', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      expect(find.text('Partner Dashboard'), findsOneWidget);
    });

    testWidgets('test_shows_three_tabs', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('Codes'), findsOneWidget);
      expect(find.text('Earnings'), findsOneWidget);
    });

    testWidgets('test_displays_dashboard_stats', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      expect(find.text('Total Earnings'), findsOneWidget);
      expect(find.text('\$500.00'), findsOneWidget);
      expect(find.text('Active Codes'), findsOneWidget);
      expect(find.text('5'), findsOneWidget);
      expect(find.text('Referrals'), findsOneWidget);
      expect(find.text('20'), findsOneWidget);
    });
  });

  group('PartnerDashboardScreen - Codes Tab', () {
    testWidgets('test_switches_to_codes_tab', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Codes'));
      await tester.pumpAndSettle();

      expect(find.text('PARTNER2024'), findsOneWidget);
      expect(find.text('15%'), findsOneWidget);
      expect(find.text('10 uses'), findsOneWidget);
    });

    testWidgets('test_displays_code_earnings', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Codes'));
      await tester.pumpAndSettle();

      expect(find.text('\$150.00'), findsOneWidget);
    });

    testWidgets('test_shows_create_code_button', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Codes'));
      await tester.pumpAndSettle();

      expect(find.text('Create Code'), findsOneWidget);
    });
  });

  group('PartnerDashboardScreen - Earnings Tab', () {
    testWidgets('test_switches_to_earnings_tab', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Earnings'));
      await tester.pumpAndSettle();

      expect(find.text('Recent Earnings'), findsOneWidget);
    });

    testWidgets('test_displays_earnings_list', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Earnings'));
      await tester.pumpAndSettle();

      expect(find.text('2026-02-11'), findsOneWidget);
      expect(find.text('PARTNER2024'), findsOneWidget);
      expect(find.text('\$25.00'), findsOneWidget);
    });
  });

  group('PartnerDashboardScreen - Non-Partner View', () {
    testWidgets('test_shows_bind_form_when_not_partner', (tester) async {
      await tester.pumpWidget(
        buildTestablePartnerDashboard(isPartner: false),
      );
      await tester.pumpAndSettle();

      expect(find.text('Become a Partner'), findsOneWidget);
      expect(find.text('Enter your partner code'), findsOneWidget);
    });

    testWidgets('test_shows_partner_code_input', (tester) async {
      await tester.pumpWidget(
        buildTestablePartnerDashboard(isPartner: false),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.text('Bind Code'), findsOneWidget);
    });

    testWidgets('test_code_input_converts_to_uppercase', (tester) async {
      await tester.pumpWidget(
        buildTestablePartnerDashboard(isPartner: false),
      );
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'partner123');
      await tester.pump();

      final TextField widget = tester.widget(find.byType(TextField));
      expect(widget.controller?.text, 'PARTNER123');
    });

    testWidgets('test_bind_button_calls_api', (tester) async {
      await tester.pumpWidget(
        buildTestablePartnerDashboard(isPartner: false),
      );
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'CODE123');
      await tester.pump();

      final bindButton = find.text('Bind Code');
      await tester.tap(bindButton);
      await tester.pumpAndSettle();

      expect(find.text('Partner code bound successfully'), findsOneWidget);
    });
  });

  group('PartnerDashboardScreen - Loading State', () {
    testWidgets('test_shows_loading_indicator_initially', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);
    });
  });

  group('PartnerDashboardScreen - Tab Navigation', () {
    testWidgets('test_maintains_tab_state_on_switch', (tester) async {
      await tester.pumpWidget(buildTestablePartnerDashboard());
      await tester.pumpAndSettle();

      // Switch to Codes tab
      await tester.tap(find.text('Codes'));
      await tester.pumpAndSettle();

      expect(find.text('PARTNER2024'), findsOneWidget);

      // Switch to Earnings tab
      await tester.tap(find.text('Earnings'));
      await tester.pumpAndSettle();

      expect(find.text('Recent Earnings'), findsOneWidget);

      // Switch back to Dashboard tab
      await tester.tap(find.text('Dashboard'));
      await tester.pumpAndSettle();

      expect(find.text('Total Earnings'), findsOneWidget);
    });
  });
}
