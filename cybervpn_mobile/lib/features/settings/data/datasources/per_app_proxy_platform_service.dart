import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb, visibleForTesting;
import 'package:flutter/services.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/installed_app.dart';

abstract class PerAppProxyPlatformService {
  bool get isSupported;
  Future<List<InstalledApp>> getInstalledApps();
  Future<String?> getCurrentPackageName();
}

class MethodChannelPerAppProxyPlatformService
    implements PerAppProxyPlatformService {
  const MethodChannelPerAppProxyPlatformService();

  static const MethodChannel _channel = MethodChannel(
    'com.cybervpn.cybervpn_mobile/per_app_proxy',
  );

  @visibleForTesting
  static bool? debugIsSupportedOverride;

  @override
  bool get isSupported {
    final override = debugIsSupportedOverride;
    if (override != null) {
      return override;
    }

    if (kIsWeb) {
      return false;
    }

    return Platform.isAndroid;
  }

  @override
  Future<List<InstalledApp>> getInstalledApps() async {
    if (!isSupported) {
      return const <InstalledApp>[];
    }

    try {
      final result = await _channel.invokeListMethod<dynamic>(
        'getInstalledApps',
      );
      if (result == null) {
        return const <InstalledApp>[];
      }

      final apps =
          result
              .whereType<Map<Object?, Object?>>()
              .map(InstalledApp.fromPlatformMap)
              .where((app) => app.packageName.isNotEmpty)
              .toList()
            ..sort(
              (left, right) => left.displayName.toLowerCase().compareTo(
                right.displayName.toLowerCase(),
              ),
            );

      return apps;
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to fetch installed apps for per-app proxy',
        error: error,
        stackTrace: stackTrace,
      );
      return const <InstalledApp>[];
    }
  }

  @override
  Future<String?> getCurrentPackageName() async {
    if (!isSupported) {
      return null;
    }

    try {
      return await _channel.invokeMethod<String>('getCurrentPackageName');
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to fetch current package name for per-app proxy',
        error: error,
        stackTrace: stackTrace,
      );
      return null;
    }
  }
}
