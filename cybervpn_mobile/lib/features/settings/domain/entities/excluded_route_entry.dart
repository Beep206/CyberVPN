import 'dart:io';

/// Semantic type of one excluded route value.
enum ExcludedRouteTargetType {
  ipv4Address,
  ipv4Cidr,
  ipv6Address,
  ipv6Cidr,
  unknown,
}

/// Typed representation of an excluded route entered by the user.
///
/// Phase 8 keeps storing the raw string value so existing runtime paths that
/// still consume string routes remain compatible while newer screens/services
/// can reason about IPv4/IPv6 and address/CIDR semantics.
class ExcludedRouteEntry {
  const ExcludedRouteEntry({required this.rawValue, required this.targetType});

  /// Original value entered by the user or restored from storage.
  final String rawValue;

  /// Best-effort semantic classification derived from [rawValue].
  final ExcludedRouteTargetType targetType;

  /// Trimmed user value used for persistence/runtime hand-off.
  String get normalizedValue => rawValue.trim();

  bool get isIpv6 =>
      targetType == ExcludedRouteTargetType.ipv6Address ||
      targetType == ExcludedRouteTargetType.ipv6Cidr;

  bool get isCidr =>
      targetType == ExcludedRouteTargetType.ipv4Cidr ||
      targetType == ExcludedRouteTargetType.ipv6Cidr;

  Map<String, dynamic> toStorageJson() => {
    'rawValue': normalizedValue,
    'targetType': targetType.name,
  };

  static ExcludedRouteEntry fromStorageJson(Map<String, dynamic> json) {
    final rawValue = (json['rawValue'] as String? ?? '').trim();
    final storedType = json['targetType'] as String?;
    final targetType = ExcludedRouteTargetType.values.firstWhere(
      (value) => value.name == storedType,
      orElse: () => inferTargetType(rawValue),
    );

    return ExcludedRouteEntry(rawValue: rawValue, targetType: targetType);
  }

  static ExcludedRouteEntry parse(String value) {
    final normalized = value.trim();
    return ExcludedRouteEntry(
      rawValue: normalized,
      targetType: inferTargetType(normalized),
    );
  }

  static ExcludedRouteTargetType inferTargetType(String value) {
    final normalized = value.trim();
    if (normalized.isEmpty) return ExcludedRouteTargetType.unknown;

    if (normalized.contains('/')) {
      final parts = normalized.split('/');
      if (parts.length != 2) return ExcludedRouteTargetType.unknown;

      final address = InternetAddress.tryParse(parts.first.trim());
      final prefixLength = int.tryParse(parts.last.trim());
      if (address == null || prefixLength == null) {
        return ExcludedRouteTargetType.unknown;
      }

      if (address.type == InternetAddressType.IPv4 &&
          prefixLength >= 0 &&
          prefixLength <= 32) {
        return ExcludedRouteTargetType.ipv4Cidr;
      }

      if (address.type == InternetAddressType.IPv6 &&
          prefixLength >= 0 &&
          prefixLength <= 128) {
        return ExcludedRouteTargetType.ipv6Cidr;
      }

      return ExcludedRouteTargetType.unknown;
    }

    final address = InternetAddress.tryParse(normalized);
    if (address == null) return ExcludedRouteTargetType.unknown;

    return switch (address.type) {
      InternetAddressType.IPv4 => ExcludedRouteTargetType.ipv4Address,
      InternetAddressType.IPv6 => ExcludedRouteTargetType.ipv6Address,
      _ => ExcludedRouteTargetType.unknown,
    };
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ExcludedRouteEntry &&
            other.rawValue == rawValue &&
            other.targetType == targetType;
  }

  @override
  int get hashCode => Object.hash(rawValue, targetType);

  @override
  String toString() =>
      'ExcludedRouteEntry(rawValue: $rawValue, targetType: $targetType)';
}
