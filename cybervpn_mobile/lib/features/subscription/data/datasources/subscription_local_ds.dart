import 'dart:convert';

import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';

abstract class SubscriptionLocalDataSource {
  Future<void> cachePlans(List<PlanEntity> plans);
  Future<List<PlanEntity>?> getCachedPlans();
  Future<void> cacheSubscription(SubscriptionEntity? subscription);
  Future<SubscriptionEntity?> getCachedSubscription();
  Future<bool> hasSubscriptionCache();
  Future<void> clearCache();
}

class SubscriptionLocalDataSourceImpl implements SubscriptionLocalDataSource {
  final LocalStorageWrapper _localStorage;

  static const String _plansKey = 'cached_plans';
  static const String _plansCacheTimestampKey = 'plans_cache_timestamp';
  static const String _subscriptionKey = 'cached_subscription';
  static const String _subscriptionCacheTimestampKey = 'subscription_cache_timestamp';
  static const int _cacheValidityMinutes = 5;

  SubscriptionLocalDataSourceImpl(this._localStorage);

  // ── Plans cache ──────────────────────────────────────────────────────────

  @override
  Future<void> cachePlans(List<PlanEntity> plans) async {
    final jsonList = plans.map(_planToJson).toList();
    await _localStorage.setString(_plansKey, jsonEncode(jsonList));
    await _localStorage.setString(
      _plansCacheTimestampKey,
      DateTime.now().toIso8601String(),
    );
  }

  @override
  Future<List<PlanEntity>?> getCachedPlans() async {
    if (!await _isCacheValid(_plansCacheTimestampKey)) return null;
    final jsonStr = await _localStorage.getString(_plansKey);
    if (jsonStr == null) return null;
    final jsonList = jsonDecode(jsonStr) as List<dynamic>;
    return jsonList.map((json) => _planFromJson(json as Map<String, dynamic>)).toList();
  }

  // ── Subscription cache ───────────────────────────────────────────────────

  @override
  Future<void> cacheSubscription(SubscriptionEntity? subscription) async {
    if (subscription == null) {
      await _localStorage.setString(_subscriptionKey, 'null');
    } else {
      await _localStorage.setString(_subscriptionKey, jsonEncode(_subscriptionToJson(subscription)));
    }
    await _localStorage.setString(
      _subscriptionCacheTimestampKey,
      DateTime.now().toIso8601String(),
    );
  }

  @override
  Future<SubscriptionEntity?> getCachedSubscription() async {
    if (!await _isCacheValid(_subscriptionCacheTimestampKey)) return null;
    final jsonStr = await _localStorage.getString(_subscriptionKey);
    if (jsonStr == null) return null;
    if (jsonStr == 'null') return null;
    final m = jsonDecode(jsonStr) as Map<String, dynamic>;
    return _subscriptionFromJson(m);
  }

  @override
  Future<bool> hasSubscriptionCache() async {
    if (!await _isCacheValid(_subscriptionCacheTimestampKey)) return false;
    final jsonStr = await _localStorage.getString(_subscriptionKey);
    return jsonStr != null;
  }

  // ── Clearing ─────────────────────────────────────────────────────────────

  @override
  Future<void> clearCache() async {
    await _localStorage.remove(_plansKey);
    await _localStorage.remove(_plansCacheTimestampKey);
    await _localStorage.remove(_subscriptionKey);
    await _localStorage.remove(_subscriptionCacheTimestampKey);
  }

  // ── TTL validation ───────────────────────────────────────────────────────

  Future<bool> _isCacheValid(String timestampKey) async {
    final timestampStr = await _localStorage.getString(timestampKey);
    if (timestampStr == null) return false;
    final timestamp = DateTime.parse(timestampStr);
    return DateTime.now().difference(timestamp).inMinutes < _cacheValidityMinutes;
  }

  // ── Serialization helpers ────────────────────────────────────────────────

  static Map<String, dynamic> _planToJson(PlanEntity plan) => {
        'id': plan.id,
        'name': plan.name,
        'description': plan.description,
        'price': plan.price,
        'currency': plan.currency,
        'duration': plan.duration.name,
        'durationDays': plan.durationDays,
        'maxDevices': plan.maxDevices,
        'trafficLimitGb': plan.trafficLimitGb,
        'isPopular': plan.isPopular,
        'isTrial': plan.isTrial,
        'storeProductId': plan.storeProductId,
        'features': plan.features,
      };

  static PlanEntity _planFromJson(Map<String, dynamic> m) => PlanEntity(
        id: m['id'] as String,
        name: m['name'] as String,
        description: m['description'] as String? ?? '',
        price: (m['price'] as num).toDouble(),
        currency: m['currency'] as String? ?? 'USD',
        duration: PlanDuration.values.firstWhere(
          (e) => e.name == (m['duration'] as String?),
          orElse: () => PlanDuration.monthly,
        ),
        durationDays: (m['durationDays'] as num?)?.toInt() ?? 30,
        maxDevices: (m['maxDevices'] as num?)?.toInt() ?? 1,
        trafficLimitGb: (m['trafficLimitGb'] as num?)?.toInt() ?? 0,
        isPopular: m['isPopular'] as bool? ?? false,
        isTrial: m['isTrial'] as bool? ?? false,
        storeProductId: m['storeProductId'] as String?,
        features: (m['features'] as List<dynamic>?)?.cast<String>(),
      );

  static Map<String, dynamic> _subscriptionToJson(SubscriptionEntity sub) => {
        'id': sub.id,
        'planId': sub.planId,
        'userId': sub.userId,
        'status': sub.status.name,
        'startDate': sub.startDate.toIso8601String(),
        'endDate': sub.endDate.toIso8601String(),
        'trafficUsedBytes': sub.trafficUsedBytes,
        'trafficLimitBytes': sub.trafficLimitBytes,
        'devicesConnected': sub.devicesConnected,
        'maxDevices': sub.maxDevices,
        'subscriptionLink': sub.subscriptionLink,
        'cancelledAt': sub.cancelledAt?.toIso8601String(),
      };

  static SubscriptionEntity _subscriptionFromJson(Map<String, dynamic> m) =>
      SubscriptionEntity(
        id: m['id'] as String,
        planId: m['planId'] as String,
        userId: m['userId'] as String? ?? '',
        status: SubscriptionStatus.values.firstWhere(
          (e) => e.name == (m['status'] as String?),
          orElse: () => SubscriptionStatus.expired,
        ),
        startDate: DateTime.parse(m['startDate'] as String),
        endDate: DateTime.parse(m['endDate'] as String),
        trafficUsedBytes: (m['trafficUsedBytes'] as num?)?.toInt() ?? 0,
        trafficLimitBytes: (m['trafficLimitBytes'] as num?)?.toInt() ?? 0,
        devicesConnected: (m['devicesConnected'] as num?)?.toInt() ?? 0,
        maxDevices: (m['maxDevices'] as num?)?.toInt() ?? 1,
        subscriptionLink: m['subscriptionLink'] as String?,
        cancelledAt: m['cancelledAt'] != null
            ? DateTime.parse(m['cancelledAt'] as String)
            : null,
      );
}
