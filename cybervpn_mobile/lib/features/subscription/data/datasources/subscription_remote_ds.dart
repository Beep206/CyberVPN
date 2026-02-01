import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';

abstract class SubscriptionRemoteDataSource {
  Future<List<PlanEntity>> fetchPlans();
  Future<SubscriptionEntity?> fetchActiveSubscription();
  Future<SubscriptionEntity> createSubscription(String planId, {String? paymentMethod});
  Future<void> cancelSubscription(String subscriptionId);
}

class SubscriptionRemoteDataSourceImpl implements SubscriptionRemoteDataSource {
  final ApiClient _apiClient;

  SubscriptionRemoteDataSourceImpl(this._apiClient);

  @override
  Future<List<PlanEntity>> fetchPlans() async {
    final response = await _apiClient.get('/plans');
    final data = response.data as List<dynamic>;
    return data.map((json) {
      final m = json as Map<String, dynamic>;
      return PlanEntity(
        id: m['id'] as String, name: m['name'] as String,
        description: m['description'] as String? ?? '',
        price: (m['price'] as num).toDouble(),
        currency: m['currency'] as String? ?? 'USD',
        duration: PlanDuration.values.firstWhere((e) => e.name == (m['duration'] as String?) , orElse: () => PlanDuration.monthly),
        trafficLimitGb: (m['traffic_limit_gb'] as num?)?.toInt(),
        maxDevices: m['max_devices'] as int? ?? 1,
        features: (m['features'] as List<dynamic>?)?.cast<String>() ?? [],
      );
    }).toList();
  }

  @override
  Future<SubscriptionEntity?> fetchActiveSubscription() async {
    try {
      final response = await _apiClient.get('/subscription/active');
      final data = response.data as Map<String, dynamic>;
      return SubscriptionEntity(
        id: data['id'] as String, planId: data['plan_id'] as String,
        planName: data['plan_name'] as String,
        status: SubscriptionStatus.values.firstWhere((e) => e.name == (data['status'] as String?), orElse: () => SubscriptionStatus.inactive),
        startDate: DateTime.parse(data['start_date'] as String),
        endDate: DateTime.parse(data['end_date'] as String),
        trafficUsedBytes: (data['traffic_used_bytes'] as num?)?.toInt() ?? 0,
        trafficLimitBytes: (data['traffic_limit_bytes'] as num?)?.toInt(),
        autoRenew: data['auto_renew'] as bool? ?? false,
      );
    } catch (_) {
      return null;
    }
  }

  @override
  Future<SubscriptionEntity> createSubscription(String planId, {String? paymentMethod}) async {
    final response = await _apiClient.post('/subscription', data: {
      'plan_id': planId, if (paymentMethod != null) 'payment_method': paymentMethod,
    });
    final data = response.data as Map<String, dynamic>;
    return SubscriptionEntity(
      id: data['id'] as String, planId: data['plan_id'] as String,
      planName: data['plan_name'] as String,
      status: SubscriptionStatus.active,
      startDate: DateTime.parse(data['start_date'] as String),
      endDate: DateTime.parse(data['end_date'] as String),
      trafficUsedBytes: 0,
      trafficLimitBytes: (data['traffic_limit_bytes'] as num?)?.toInt(),
      autoRenew: data['auto_renew'] as bool? ?? false,
    );
  }

  @override
  Future<void> cancelSubscription(String subscriptionId) async {
    await _apiClient.post('/subscription/$subscriptionId/cancel');
  }
}
