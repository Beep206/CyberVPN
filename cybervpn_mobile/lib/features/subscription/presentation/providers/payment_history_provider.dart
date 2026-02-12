import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';

/// Provides paginated payment history for the current user.
///
/// Fetches from the subscription repository and handles pagination.
final paymentHistoryProvider =
    FutureProvider.autoDispose<PaginatedPaymentHistory>((ref) async {
  final SubscriptionRepository repository = ref.watch(subscriptionRepositoryProvider);
  final Result<PaginatedPaymentHistory> result = await repository.getPaymentHistory(limit: 50);

  return result.dataOrNull ??
      const PaginatedPaymentHistory(
        items: [],
        total: 0,
        offset: 0,
        limit: 0,
      );
});
