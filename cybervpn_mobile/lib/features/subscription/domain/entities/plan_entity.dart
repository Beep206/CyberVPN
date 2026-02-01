import 'package:freezed_annotation/freezed_annotation.dart';

part 'plan_entity.freezed.dart';

enum PlanDuration { monthly, quarterly, yearly, lifetime }

@freezed
abstract class PlanEntity with _$PlanEntity {
  const factory PlanEntity({
    required String id,
    required String name,
    required String description,
    required double price,
    required String currency,
    required PlanDuration duration,
    required int durationDays,
    required int maxDevices,
    required int trafficLimitGb,
    @Default(false) bool isPopular,
    @Default(false) bool isTrial,
    String? storeProductId,
    List<String>? features,
  }) = _PlanEntity;
}
