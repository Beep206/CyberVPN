import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

const String mobilePublicCatalogChannel = 'web';

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

class CommercialCatalogRequest {
  const CommercialCatalogRequest({
    this.channel = mobilePublicCatalogChannel,
    this.country,
    this.currency,
    this.uiLocale,
    this.urlLocale,
    this.storefrontKey,
  });

  final String channel;
  final String? country;
  final String? currency;
  final String? uiLocale;
  final String? urlLocale;
  final String? storefrontKey;

  Map<String, dynamic> toQueryParameters() {
    return <String, dynamic>{
      'channel': channel,
      if (country != null) 'country': country,
      if (currency != null) 'currency': currency,
      if (uiLocale != null) 'uiLocale': uiLocale,
      if (urlLocale != null) 'urlLocale': urlLocale,
      if (storefrontKey != null) 'storefrontKey': storefrontKey,
    };
  }
}

class CommercialCatalogContext {
  const CommercialCatalogContext({
    required this.uiLocale,
    required this.displayCountry,
    required this.pricingCountry,
    required this.paymentCountry,
    required this.currency,
    required this.confidence,
    required this.selectableCountries,
    required this.selectableCurrencies,
    required this.paymentMethods,
    required this.cacheKey,
    required this.resolutionTrace,
  });

  final String uiLocale;
  final String displayCountry;
  final String pricingCountry;
  final String paymentCountry;
  final String currency;
  final String confidence;
  final List<String> selectableCountries;
  final List<String> selectableCurrencies;
  final Map<String, dynamic> paymentMethods;
  final String cacheKey;
  final List<String> resolutionTrace;

  factory CommercialCatalogContext.fromJson(Map<String, dynamic> json) {
    return CommercialCatalogContext(
      uiLocale: json['uiLocale'] as String? ?? 'en-EN',
      displayCountry: json['displayCountry'] as String? ?? 'US',
      pricingCountry: json['pricingCountry'] as String? ?? 'US',
      paymentCountry: json['paymentCountry'] as String? ?? 'US',
      currency: json['currency'] as String? ?? 'USD',
      confidence: json['confidence'] as String? ?? 'fallback',
      selectableCountries:
          (json['selectableCountries'] as List<dynamic>?)?.cast<String>() ??
          const <String>[],
      selectableCurrencies:
          (json['selectableCurrencies'] as List<dynamic>?)?.cast<String>() ??
          const <String>[],
      paymentMethods:
          (json['paymentMethods'] as Map?)?.cast<String, dynamic>() ??
          const <String, dynamic>{},
      cacheKey: json['cacheKey'] as String? ?? '',
      resolutionTrace:
          (json['resolutionTrace'] as List<dynamic>?)?.cast<String>() ??
          const <String>[],
    );
  }
}

class CommercialCatalogSnapshot {
  const CommercialCatalogSnapshot({
    required this.catalogVersion,
    required this.cacheKey,
    required this.context,
    required this.plans,
    required this.sourceChannel,
    required this.iapStorefrontActive,
  });

  final String catalogVersion;
  final String cacheKey;
  final CommercialCatalogContext context;
  final List<PlanEntity> plans;
  final String sourceChannel;

  /// Native IAP is intentionally not activated by the public catalog read path.
  ///
  /// The app still contains RevenueCat restore plumbing, but this catalog
  /// integration does not create store products or change purchase behavior.
  final bool iapStorefrontActive;
}

abstract class SubscriptionRemoteDataSource {
  Future<CommercialCatalogSnapshot> fetchCommercialCatalog({
    CommercialCatalogRequest request = const CommercialCatalogRequest(),
  });
  Future<List<PlanEntity>> fetchPlans();
  Future<SubscriptionEntity?> fetchActiveSubscription();
  Future<SubscriptionEntity> createSubscription(
    String planId, {
    String? paymentMethod,
  });
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
  Future<CommercialCatalogSnapshot> fetchCommercialCatalog({
    CommercialCatalogRequest request = const CommercialCatalogRequest(),
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiConstants.commercialCatalog,
      queryParameters: request.toQueryParameters(),
    );
    final data = response.data ?? <String, dynamic>{};
    final context = CommercialCatalogContext.fromJson(
      (data['context'] as Map?)?.cast<String, dynamic>() ??
          const <String, dynamic>{},
    );
    final metadata =
        (data['metadata'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final sourceChannel =
        metadata['channel'] as String? ?? request.channel;

    return CommercialCatalogSnapshot(
      catalogVersion: data['catalogVersion'] as String? ?? '',
      cacheKey: data['cacheKey'] as String? ?? '',
      context: context,
      sourceChannel: sourceChannel,
      iapStorefrontActive: false,
      plans: _parseCommercialCatalogPlans(
        (data['plans'] as List<dynamic>?) ?? const <dynamic>[],
        fallbackCurrency: context.currency,
      ),
    );
  }

  @override
  Future<List<PlanEntity>> fetchPlans() async {
    final catalog = await fetchCommercialCatalog();
    return catalog.plans;
  }

  List<PlanEntity> _parseCommercialCatalogPlans(
    List<dynamic> plans, {
    required String fallbackCurrency,
  }) {
    final mapped = <PlanEntity>[];
    for (final planJson in plans) {
      final plan = (planJson as Map).cast<String, dynamic>();
      final billingPeriods =
          (plan['billingPeriods'] as List<dynamic>?) ?? const <dynamic>[];
      final planCode = plan['planCode'] as String? ?? '';
      final metadata =
          (plan['metadata'] as Map?)?.cast<String, dynamic>() ??
          const <String, dynamic>{};
      final marketingBadge = _readString(
        (metadata['features'] as Map?)?['marketing_badge'],
      );

      for (final periodJson in billingPeriods) {
        final period = (periodJson as Map).cast<String, dynamic>();
        final quote =
            (period['quote'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{};
        final displayPrice =
            (period['displayPrice'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{};
        final durationDays =
            (period['durationDays'] as num?)?.toInt() ??
            (quote['billingPeriodDays'] as num?)?.toInt() ??
            30;
        final trafficLimitBytes = (plan['trafficLimitBytes'] as num?)?.toInt();

        mapped.add(
          PlanEntity(
            id:
                quote['planId'] as String? ??
                period['planId'] as String? ??
                period['catalogItemKey'] as String? ??
                planCode,
            name: _planDisplayName(
              plan['displayName'] as String? ?? planCode,
              durationDays,
            ),
            description: '',
            price: _moneyAmount(displayPrice['amount']),
            currency: displayPrice['currency'] as String? ?? fallbackCurrency,
            duration: _durationFromDays(durationDays),
            durationDays: durationDays,
            trafficLimitGb: _bytesToGiB(trafficLimitBytes),
            maxDevices: (plan['devicesIncluded'] as num?)?.toInt() ?? 1,
            isPopular:
                planCode == 'plus' ||
                marketingBadge?.toLowerCase().contains('popular') == true,
            isTrial: plan['trialEligible'] as bool? ?? false,
            features: const <String>[],
          ),
        );
      }
    }

    mapped.sort((left, right) {
      final codeOrder = _planOrder(left.name).compareTo(_planOrder(right.name));
      if (codeOrder != 0) {
        return codeOrder;
      }
      return left.durationDays.compareTo(right.durationDays);
    });
    return mapped;
  }

  PlanDuration _durationFromDays(int days) {
    return switch (days) {
      30 => PlanDuration.monthly,
      90 => PlanDuration.quarterly,
      180 => PlanDuration.semiannual,
      365 => PlanDuration.yearly,
      _ when days >= 36500 => PlanDuration.lifetime,
      _ => PlanDuration.monthly,
    };
  }

  String _planDisplayName(String familyName, int durationDays) {
    if (durationDays == 30) {
      return familyName;
    }
    return '$familyName ${durationDays}d';
  }

  double _moneyAmount(Object? value) {
    if (value is num) {
      return value.toDouble();
    }
    if (value is String) {
      return double.tryParse(value) ?? 0;
    }
    return 0;
  }

  int _bytesToGiB(int? value) {
    if (value == null || value <= 0) {
      return 0;
    }
    return (value / (1024 * 1024 * 1024)).round();
  }

  String? _readString(Object? value) {
    if (value is String && value.trim().isNotEmpty) {
      return value.trim();
    }
    return null;
  }

  int _planOrder(String name) {
    final normalized = name.toLowerCase();
    if (normalized.startsWith('basic')) return 1;
    if (normalized.startsWith('plus')) return 2;
    if (normalized.startsWith('pro')) return 3;
    if (normalized.startsWith('max')) return 4;
    return 99;
  }

  @override
  Future<SubscriptionEntity?> fetchActiveSubscription() async {
    try {
      final entitlementResponse = await _apiClient.get<Map<String, dynamic>>(
        ApiConstants.activeSubscription,
      );
      final entitlementSnapshot =
          entitlementResponse.data ?? <String, dynamic>{};
      if ((entitlementSnapshot['status'] as String? ?? 'none') == 'none') {
        return null;
      }

      final serviceStateResponse = await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.currentServiceState,
        data: const {'provider_name': 'remnawave'},
      );
      final serviceState = serviceStateResponse.data ?? <String, dynamic>{};

      return _parseCanonicalSubscription(
        entitlementSnapshot: entitlementSnapshot,
        serviceState: serviceState,
      );
    } catch (e) {
      AppLogger.warning(
        'Failed to parse subscription data',
        error: e,
        category: 'subscription',
      );
      return null;
    }
  }

  @override
  Future<SubscriptionEntity> createSubscription(
    String planId, {
    String? paymentMethod,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/subscription',
      data: {
        'plan_id': planId,
        ...?paymentMethod == null
            ? null
            : <String, dynamic>{'payment_method': paymentMethod},
      },
    );
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
    await _apiClient.post<Map<String, dynamic>>(
      '/subscription/$subscriptionId/cancel',
    );
  }

  @override
  Future<PaginatedPaymentHistory> fetchPaymentHistory({
    int offset = 0,
    int limit = 20,
  }) async {
    final response = await _apiClient.get<List<dynamic>>(
      ApiConstants.paymentHistory,
      queryParameters: {'offset': offset, 'limit': limit},
    );
    final data = response.data ?? const <dynamic>[];
    final items =
        data
            .map(
              (json) =>
                  _mapOrderToPaymentHistoryEntry(json as Map<String, dynamic>),
            )
            .toList()
          ..sort((left, right) => right.createdAt.compareTo(left.createdAt));

    return PaginatedPaymentHistory(
      items: items,
      total: offset + items.length,
      offset: offset,
      limit: limit,
    );
  }

  @override
  Future<SubscriptionEntity> redeemInviteCode(String code) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiConstants.redeemInviteCode,
      data: {'code': code},
    );
    final body = response.data!;
    final subData = body['subscription'] as Map<String, dynamic>;
    AppLogger.info('Invite code redeemed successfully: $code');
    return _parseSubscription(subData);
  }

  @override
  Future<Map<String, dynamic>> applyPromoCode(
    String code,
    String planId,
  ) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiConstants.validatePromoCode,
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
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiConstants.trialStatus,
    );
    final body = response.data!;
    return {
      'is_eligible': body['is_eligible'] as bool? ?? false,
      'days_remaining': (body['days_remaining'] as num?)?.toInt(),
      'trial_used': body['trial_used'] as bool? ?? false,
    };
  }

  @override
  Future<SubscriptionEntity> activateTrial() async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiConstants.trialActivate,
    );
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

  SubscriptionEntity _parseCanonicalSubscription({
    required Map<String, dynamic> entitlementSnapshot,
    required Map<String, dynamic> serviceState,
  }) {
    final effectiveEntitlements =
        (entitlementSnapshot['effective_entitlements'] as Map?)
            ?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final purchaseContext =
        (serviceState['purchase_context'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final serviceIdentity =
        (serviceState['service_identity'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final provisioningProfile =
        (serviceState['provisioning_profile'] as Map?)
            ?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final deliveryChannel =
        (serviceState['access_delivery_channel'] as Map?)
            ?.cast<String, dynamic>() ??
        const <String, dynamic>{};

    final expiresAt = _parseDateTime(entitlementSnapshot['expires_at']);
    final periodDays = (entitlementSnapshot['period_days'] as num?)?.toInt();
    final startDate = expiresAt != null && periodDays != null
        ? expiresAt.subtract(Duration(days: periodDays))
        : DateTime.now().toUtc();

    return SubscriptionEntity(
      id:
          _firstNonEmptyString([
            purchaseContext['active_entitlement_grant_id']?.toString(),
            serviceIdentity['id']?.toString(),
            purchaseContext['source_order_id']?.toString(),
            entitlementSnapshot['plan_uuid']?.toString(),
          ]) ??
          'canonical-subscription',
      planId:
          _firstNonEmptyString([
            entitlementSnapshot['plan_uuid']?.toString(),
            entitlementSnapshot['plan_code']?.toString(),
            entitlementSnapshot['display_name']?.toString(),
          ]) ??
          'unknown',
      userId: serviceState['customer_account_id']?.toString() ?? '',
      status: _mapCanonicalSubscriptionStatus(
        entitlementSnapshot['status'] as String?,
      ),
      startDate: startDate,
      endDate: expiresAt ?? startDate,
      trafficUsedBytes: 0,
      trafficLimitBytes: _trafficLimitBytesFromEntitlements(
        effectiveEntitlements,
      ),
      devicesConnected: 0,
      maxDevices: (effectiveEntitlements['device_limit'] as num?)?.toInt() ?? 1,
      subscriptionLink: _extractSubscriptionLink(
        provisioningPayload:
            (provisioningProfile['provisioning_payload'] as Map?)
                ?.cast<String, dynamic>() ??
            const <String, dynamic>{},
        deliveryPayload:
            (deliveryChannel['delivery_payload'] as Map?)
                ?.cast<String, dynamic>() ??
            const <String, dynamic>{},
      ),
      cancelledAt: null,
    );
  }

  PaymentHistoryEntry _mapOrderToPaymentHistoryEntry(
    Map<String, dynamic> order,
  ) {
    final items = (order['items'] as List<dynamic>?) ?? const <dynamic>[];
    final firstItem = items.isNotEmpty
        ? (items.first as Map).cast<String, dynamic>()
        : const <String, dynamic>{};
    final pricingSnapshot =
        (order['pricing_snapshot'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};
    final offerSnapshot =
        (pricingSnapshot['offer'] as Map?)?.cast<String, dynamic>() ??
        const <String, dynamic>{};

    return PaymentHistoryEntry(
      id: order['id']?.toString() ?? '',
      planName:
          _firstNonEmptyString([
            firstItem['display_name'] as String?,
            offerSnapshot['display_name'] as String?,
            order['subscription_plan_id']?.toString(),
            'Order',
          ]) ??
          'Order',
      amount:
          ((order['displayed_price'] as num?) ??
                  (order['gateway_amount'] as num?) ??
                  (order['wallet_amount'] as num?) ??
                  0)
              .toDouble(),
      currency: order['currency_code'] as String? ?? 'USD',
      status: _mapCanonicalPaymentStatus(
        settlementStatus: order['settlement_status'] as String?,
        orderStatus: order['order_status'] as String?,
      ),
      createdAt: _parseDateTime(order['created_at']) ?? DateTime.now().toUtc(),
    );
  }

  SubscriptionStatus _mapCanonicalSubscriptionStatus(String? status) {
    return switch (status) {
      'active' => SubscriptionStatus.active,
      'trial' => SubscriptionStatus.trial,
      'cancelled' => SubscriptionStatus.cancelled,
      'pending' || 'pending_payment' => SubscriptionStatus.pending,
      _ => SubscriptionStatus.expired,
    };
  }

  String _mapCanonicalPaymentStatus({
    required String? settlementStatus,
    required String? orderStatus,
  }) {
    final normalizedSettlement = settlementStatus?.trim().toLowerCase();
    if (normalizedSettlement != null &&
        normalizedSettlement.isNotEmpty &&
        normalizedSettlement != 'pending_payment') {
      return normalizedSettlement;
    }
    return orderStatus?.trim().toLowerCase() ?? 'unknown';
  }

  int _trafficLimitBytesFromEntitlements(
    Map<String, dynamic> effectiveEntitlements,
  ) {
    final rawLimit = effectiveEntitlements['traffic_limit_bytes'];
    if (rawLimit is num) {
      return rawLimit.toInt();
    }

    final label = effectiveEntitlements['display_traffic_label'] as String?;
    if (label == null) {
      return 0;
    }

    final match = RegExp(
      r'(\d+(?:\.\d+)?)\s*(GB|TB)',
      caseSensitive: false,
    ).firstMatch(label);
    if (match == null) {
      return 0;
    }

    final value = double.tryParse(match.group(1) ?? '');
    final unit = match.group(2)?.toUpperCase();
    if (value == null || unit == null) {
      return 0;
    }

    final multiplier = unit == 'TB'
        ? 1024 * 1024 * 1024 * 1024
        : 1024 * 1024 * 1024;
    return (value * multiplier).round();
  }

  String? _extractSubscriptionLink({
    required Map<String, dynamic> provisioningPayload,
    required Map<String, dynamic> deliveryPayload,
  }) {
    return _firstNonEmptyString([
      deliveryPayload['subscription_url'] as String?,
      deliveryPayload['subscriptionUrl'] as String?,
      deliveryPayload['config_url'] as String?,
      deliveryPayload['configUrl'] as String?,
      deliveryPayload['profile_url'] as String?,
      deliveryPayload['profileUrl'] as String?,
      provisioningPayload['subscription_url'] as String?,
      provisioningPayload['subscriptionUrl'] as String?,
      provisioningPayload['config_url'] as String?,
      provisioningPayload['configUrl'] as String?,
    ]);
  }

  DateTime? _parseDateTime(Object? value) {
    if (value is! String || value.isEmpty) {
      return null;
    }
    return DateTime.tryParse(value);
  }

  String? _firstNonEmptyString(List<String?> values) {
    for (final value in values) {
      if (value != null && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return null;
  }
}
