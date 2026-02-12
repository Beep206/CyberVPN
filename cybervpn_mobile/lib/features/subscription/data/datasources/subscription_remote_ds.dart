import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// A payment history entry returned from the API.
class PaymentHistoryEntry {
  final String id;
  final String planName;
  final double amount;
  final String currency;
  final String status;
  final DateTime createdAt;

  const PaymentHistoryEntry({
    required this.id,
    required this.planName,
    required this.amount,
    required this.currency,
    required this.status,
    required this.createdAt,
  });

  factory PaymentHistoryEntry.fromJson(Map<String, dynamic> json) {
    return PaymentHistoryEntry(
      id: json['id'] as String,
      planName: json['plan_name'] as String? ?? '',
      amount: (json['amount'] as num).toDouble(),
      currency: json['currency'] as String? ?? 'USD',
      status: json['status'] as String? ?? 'unknown',
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

/// Paginated response for payment history.
class PaginatedPaymentHistory {
  final List<PaymentHistoryEntry> items;
  final int total;
  final int offset;
  final int limit;

  const PaginatedPaymentHistory({
    required this.items,
    required this.total,
    required this.offset,
    required this.limit,
  });

  bool get hasMore => offset + items.length < total;
}

abstract class SubscriptionRemoteDataSource {
  Future<List<PlanEntity>> fetchPlans();
  Future<SubscriptionEntity?> fetchActiveSubscription();
  Future<SubscriptionEntity> createSubscription(String planId, {String? paymentMethod});
  Future<void> cancelSubscription(String subscriptionId);
  Future<PaginatedPaymentHistory> fetchPaymentHistory({
    int offset = 0,
    int limit = 20,
  });
  Future<SubscriptionEntity> redeemInviteCode(String code);
  Future<Map<String, dynamic>> applyPromoCode(String code, String planId);
  Future<Map<String, dynamic>> getTrialStatus();
  Future<SubscriptionEntity> activateTrial();
}

class SubscriptionRemoteDataSourceImpl implements SubscriptionRemoteDataSource {
  final ApiClient _apiClient;

  SubscriptionRemoteDataSourceImpl(this._apiClient);

  @override
  Future<List<PlanEntity>> fetchPlans() async {
    final response = await _apiClient.get<Map<String, dynamic>>('/plans');
    final data = response.data as List<dynamic>;
    return data.map((json) {
      final m = json as Map<String, dynamic>;
      final duration = PlanDuration.values.firstWhere(
        (e) => e.name == (m['duration'] as String?),
        orElse: () => PlanDuration.monthly,
      );
      return PlanEntity(
        id: m['id'] as String,
        name: m['name'] as String,
        description: m['description'] as String? ?? '',
        price: (m['price'] as num).toDouble(),
        currency: m['currency'] as String? ?? 'USD',
        duration: duration,
        durationDays: (m['duration_days'] as num?)?.toInt() ?? _durationToDays(duration),
        trafficLimitGb: (m['traffic_limit_gb'] as num?)?.toInt() ?? 0,
        maxDevices: (m['max_devices'] as num?)?.toInt() ?? 1,
        features: (m['features'] as List<dynamic>?)?.cast<String>() ?? [],
      );
    }).toList();
  }

  int _durationToDays(PlanDuration duration) {
    return switch (duration) {
      PlanDuration.monthly => 30,
      PlanDuration.quarterly => 90,
      PlanDuration.yearly => 365,
      PlanDuration.lifetime => 36500,
    };
  }

  @override
  Future<SubscriptionEntity?> fetchActiveSubscription() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>('/subscription/active');
      final data = response.data as Map<String, dynamic>;
      return SubscriptionEntity(
        id: data['id'] as String,
        planId: data['plan_id'] as String,
        userId: data['user_id'] as String? ?? '',
        status: SubscriptionStatus.values.firstWhere(
          (e) => e.name == (data['status'] as String?),
          orElse: () => SubscriptionStatus.expired,
        ),
        startDate: DateTime.parse(data['start_date'] as String),
        endDate: DateTime.parse(data['end_date'] as String),
        trafficUsedBytes: (data['traffic_used_bytes'] as num?)?.toInt() ?? 0,
        trafficLimitBytes: (data['traffic_limit_bytes'] as num?)?.toInt() ?? 0,
        maxDevices: (data['max_devices'] as num?)?.toInt() ?? 1,
      );
    } catch (e) {
      AppLogger.warning('Failed to parse subscription data', error: e, category: 'subscription');
      return null;
    }
  }

  @override
  Future<SubscriptionEntity> createSubscription(String planId, {String? paymentMethod}) async {
    final response = await _apiClient.post<Map<String, dynamic>>('/subscription', data: {
      'plan_id': planId, ?'payment_method': paymentMethod,
    });
    final data = response.data as Map<String, dynamic>;
    return SubscriptionEntity(
      id: data['id'] as String,
      planId: data['plan_id'] as String,
      userId: data['user_id'] as String? ?? '',
      status: SubscriptionStatus.active,
      startDate: DateTime.parse(data['start_date'] as String),
      endDate: DateTime.parse(data['end_date'] as String),
      trafficUsedBytes: 0,
      trafficLimitBytes: (data['traffic_limit_bytes'] as num?)?.toInt() ?? 0,
      maxDevices: (data['max_devices'] as num?)?.toInt() ?? 1,
    );
  }

  @override
  Future<void> cancelSubscription(String subscriptionId) async {
    await _apiClient.post<Map<String, dynamic>>('/subscription/$subscriptionId/cancel');
  }

  @override
  Future<PaginatedPaymentHistory> fetchPaymentHistory({
    int offset = 0,
    int limit = 20,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/payments/history',
      queryParameters: {'offset': offset, 'limit': limit},
    );
    final body = response.data!;
    final data = (body['items'] as List<dynamic>?) ?? [];
    final total = body['total'] as int? ?? data.length;

    return PaginatedPaymentHistory(
      items: data
          .map((json) => PaymentHistoryEntry.fromJson(json as Map<String, dynamic>))
          .toList(),
      total: total,
      offset: offset,
      limit: limit,
    );
  }

  @override
  Future<SubscriptionEntity> redeemInviteCode(String code) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/invites/redeem',
      data: {'code': code},
    );
    final body = response.data!;
    final subData = body['subscription'] as Map<String, dynamic>;
    AppLogger.info('Invite code redeemed successfully: $code');
    return _parseSubscription(subData);
  }

  @override
  Future<Map<String, dynamic>> applyPromoCode(String code, String planId) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/promo/validate',
      data: {'code': code, 'plan_id': planId},
    );
    final body = response.data!;
    AppLogger.info('Promo code validated successfully: $code');
    return {
      'discount_amount': (body['discount_amount'] as num?)?.toDouble() ?? 0.0,
      'final_price': (body['final_price'] as num?)?.toDouble() ?? 0.0,
      'message': body['message'] as String? ?? '',
    };
  }

  @override
  Future<Map<String, dynamic>> getTrialStatus() async {
    final response = await _apiClient.get<Map<String, dynamic>>('/trial/status');
    final body = response.data!;
    return {
      'is_eligible': body['is_eligible'] as bool? ?? false,
      'days_remaining': (body['days_remaining'] as num?)?.toInt(),
      'trial_used': body['trial_used'] as bool? ?? false,
    };
  }

  @override
  Future<SubscriptionEntity> activateTrial() async {
    final response = await _apiClient.post<Map<String, dynamic>>('/trial/activate');
    final body = response.data!;
    final subData = body['subscription'] as Map<String, dynamic>;
    AppLogger.info('Trial activated successfully');
    return _parseSubscription(subData);
  }

  /// Helper method to parse subscription data from API response.
  SubscriptionEntity _parseSubscription(Map<String, dynamic> data) {
    return SubscriptionEntity(
      id: data['id'] as String,
      planId: data['plan_id'] as String,
      userId: data['user_id'] as String? ?? '',
      status: SubscriptionStatus.values.firstWhere(
        (e) => e.name == (data['status'] as String?),
        orElse: () => SubscriptionStatus.expired,
      ),
      startDate: DateTime.parse(data['start_date'] as String),
      endDate: DateTime.parse(data['end_date'] as String),
      trafficUsedBytes: (data['traffic_used_bytes'] as num?)?.toInt() ?? 0,
      trafficLimitBytes: (data['traffic_limit_bytes'] as num?)?.toInt() ?? 0,
      maxDevices: (data['max_devices'] as num?)?.toInt() ?? 1,
    );
  }
}
