import 'package:freezed_annotation/freezed_annotation.dart';

part 'routing_profile.freezed.dart';

/// Supported actions for a single traffic routing rule.
enum RoutingRuleAction { proxy, direct, block }

/// Supported match strategies for a single routing rule.
enum RoutingRuleMatchType {
  domain,
  domainSuffix,
  domainKeyword,
  ipCidr,
  geoSite,
  geoIp,
  processName,
  packageName,
}

/// Immutable routing rule definition stored in settings.
@freezed
sealed class RoutingRule with _$RoutingRule {
  const RoutingRule._();

  const factory RoutingRule({
    required String id,
    required RoutingRuleMatchType matchType,
    required String value,
    @Default(RoutingRuleAction.proxy) RoutingRuleAction action,
    @Default(true) bool enabled,
    String? note,
  }) = _RoutingRule;

  factory RoutingRule.fromStorageJson(Map<String, dynamic> json) {
    return RoutingRule(
      id: json['id'] as String? ?? '',
      matchType: _readEnum(
        json['matchType'] as String?,
        RoutingRuleMatchType.values,
        RoutingRuleMatchType.domain,
      ),
      value: json['value'] as String? ?? '',
      action: _readEnum(
        json['action'] as String?,
        RoutingRuleAction.values,
        RoutingRuleAction.proxy,
      ),
      enabled: json['enabled'] as bool? ?? true,
      note: json['note'] as String?,
    );
  }

  Map<String, dynamic> toStorageJson() {
    return {
      'id': id,
      'matchType': matchType.name,
      'value': value,
      'action': action.name,
      'enabled': enabled,
      if (note != null) 'note': note,
    };
  }
}

/// Immutable routing profile grouping a named list of routing rules.
@freezed
sealed class RoutingProfile with _$RoutingProfile {
  const RoutingProfile._();

  const factory RoutingProfile({
    required String id,
    required String name,
    @Default(true) bool enabled,
    @Default(<RoutingRule>[]) List<RoutingRule> rules,
    String? description,
  }) = _RoutingProfile;

  factory RoutingProfile.fromStorageJson(Map<String, dynamic> json) {
    final rawRules = json['rules'];
    final rules = rawRules is List
        ? rawRules
              .whereType<Map>()
              .map(
                (rule) => RoutingRule.fromStorageJson(
                  Map<String, dynamic>.from(rule),
                ),
              )
              .toList()
        : const <RoutingRule>[];

    return RoutingProfile(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? true,
      rules: rules,
      description: json['description'] as String?,
    );
  }

  Map<String, dynamic> toStorageJson() {
    return {
      'id': id,
      'name': name,
      'enabled': enabled,
      'rules': rules.map((rule) => rule.toStorageJson()).toList(),
      if (description != null) 'description': description,
    };
  }
}

T _readEnum<T extends Enum>(String? stored, List<T> values, T defaultValue) {
  if (stored == null) return defaultValue;
  return values.firstWhere(
    (value) => value.name == stored,
    orElse: () => defaultValue,
  );
}
