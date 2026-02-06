import 'package:freezed_annotation/freezed_annotation.dart';

part 'subscription_entity.freezed.dart';

enum SubscriptionStatus { active, expired, cancelled, pending, trial }

@freezed
sealed class SubscriptionEntity with _$SubscriptionEntity {
  const factory SubscriptionEntity({
    required String id,
    required String planId,
    required String userId,
    required SubscriptionStatus status,
    required DateTime startDate,
    required DateTime endDate,
    required int trafficUsedBytes,
    required int trafficLimitBytes,
    @Default(0) int devicesConnected,
    required int maxDevices,
    String? subscriptionLink,
    DateTime? cancelledAt,
  }) = _SubscriptionEntity;
}
