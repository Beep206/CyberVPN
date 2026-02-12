import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' as failures;
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';
import 'package:cybervpn_mobile/features/partner/domain/repositories/partner_repository.dart';
import 'package:cybervpn_mobile/features/partner/presentation/providers/partner_provider.dart';
import 'package:cybervpn_mobile/features/partner/presentation/screens/partner_dashboard_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockPartnerRepository implements PartnerRepository {
  final bool _isAvailable = true;
  bool _isPartner = true;
  PartnerInfo? partnerInfo;
  List<PartnerCode> codes = [];
  List<Earnings> earningsList = [];
  bool shouldFail = false;

  @override
  Future<Result<bool>> isAvailable() async =>
      shouldFail
          ? const Failure(failures.ServerFailure(message: 'Error'))
          : Success(_isAvailable);

  @override
  Future<Result<bool>> isPartner({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async =>
      shouldFail
          ? const Failure(failures.ServerFailure(message: 'Error'))
          : Success(_isPartner);

  @override
  Future<Result<PartnerInfo>> getPartnerInfo({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    if (shouldFail || partnerInfo == null) {
      return const Failure(
          failures.ServerFailure(message: 'Not a partner'));
    }
    return Success(partnerInfo!);
  }

  @override
  Future<Result<List<PartnerCode>>> getPartnerCodes({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async =>
      shouldFail
          ? const Failure(failures.ServerFailure(message: 'Error'))
          : Success(codes);

  @override
  Future<Result<PartnerCode>> createPartnerCode({
    required double markup,
    String? description,
  }) async =>
      const Failure(failures.ServerFailure(message: 'Not implemented'));

  @override
  Future<Result<PartnerCode>> updateCodeMarkup({
    required String code,
    required double markup,
  }) async =>
      const Failure(failures.ServerFailure(message: 'Not implemented'));

  @override
  Future<Result<PartnerCode>> toggleCodeStatus({
    required String code,
    required bool isActive,
  }) async =>
      const Failure(failures.ServerFailure(message: 'Not implemented'));

  @override
  Future<Result<List<Earnings>>> getEarnings({int limit = 50}) async =>
      shouldFail
          ? const Failure(failures.ServerFailure(message: 'Error'))
          : Success(earningsList);

  @override
  Future<Result<BindCodeResult>> bindPartnerCode(String code) async =>
      const Success(BindCodeResult(
        success: true,
        message: 'Partner code bound successfully',
      ));

  @override
  Future<Result<void>> sharePartnerCode(String code) async =>
      const Success(null);
}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestablePartnerDashboard({
  required MockPartnerRepository mockRepo,
}) {
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
  group('PartnerDashboardScreen - Loading State', () {
    testWidgets('test_shows_loading_indicator_initially', (tester) async {
      final mockRepo = MockPartnerRepository();
      mockRepo.partnerInfo = PartnerInfo(
        tier: PartnerTier.bronze,
        clientCount: 0,
        totalEarnings: 0,
        availableBalance: 0,
        commissionRate: 10,
        partnerSince: DateTime(2026, 1, 1),
      );

      await tester.pumpWidget(
        buildTestablePartnerDashboard(mockRepo: mockRepo),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);
    });
  });

  group('PartnerDashboardScreen - Non-Partner View', () {
    testWidgets('test_shows_bind_form_when_not_partner', (tester) async {
      final mockRepo = MockPartnerRepository();
      mockRepo._isPartner = false;

      await tester.pumpWidget(
        buildTestablePartnerDashboard(mockRepo: mockRepo),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.handshake_outlined), findsOneWidget);
    });
  });
}
