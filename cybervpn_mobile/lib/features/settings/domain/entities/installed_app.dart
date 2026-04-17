import 'package:flutter/foundation.dart';

/// Installed application metadata used by Per-App Proxy settings.
@immutable
class InstalledApp {
  const InstalledApp({
    required this.packageName,
    required this.displayName,
    this.isSystemApp = false,
  });

  final String packageName;
  final String displayName;
  final bool isSystemApp;

  factory InstalledApp.fromPlatformMap(Map<Object?, Object?> map) {
    return InstalledApp(
      packageName: (map['packageName'] as String?)?.trim() ?? '',
      displayName: (map['displayName'] as String?)?.trim().isNotEmpty == true
          ? (map['displayName'] as String).trim()
          : ((map['packageName'] as String?)?.trim() ?? ''),
      isSystemApp: map['isSystemApp'] as bool? ?? false,
    );
  }

  Map<String, Object?> toPlatformMap() => {
    'packageName': packageName,
    'displayName': displayName,
    'isSystemApp': isSystemApp,
  };

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is InstalledApp &&
            runtimeType == other.runtimeType &&
            packageName == other.packageName &&
            displayName == other.displayName &&
            isSystemApp == other.isSystemApp;
  }

  @override
  int get hashCode => Object.hash(packageName, displayName, isSystemApp);

  @override
  String toString() {
    return 'InstalledApp('
        'packageName: $packageName, '
        'displayName: $displayName, '
        'isSystemApp: $isSystemApp'
        ')';
  }
}
