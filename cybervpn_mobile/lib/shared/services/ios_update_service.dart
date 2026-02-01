import 'dart:io';

import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// iOS-specific update service.
///
/// Opens App Store to the app's page for manual update.
/// iOS does not support in-app update APIs like Android.
class IosUpdateService {
  /// App Store ID for CyberVPN.
  ///
  /// TODO: Replace with actual App Store ID once app is published.
  /// Find this ID in App Store Connect after app submission.
  static const String _appStoreId = 'YOUR_APP_STORE_ID';

  /// Constructs the App Store URL for this app.
  String get appStoreUrl => 'https://apps.apple.com/app/id$_appStoreId';

  /// Opens the App Store to the CyberVPN app page.
  ///
  /// Returns `true` if successfully opened, `false` otherwise.
  Future<bool> openAppStore() async {
    if (!Platform.isIOS) {
      AppLogger.warning(
        'IosUpdateService called on non-iOS platform',
        category: 'IosUpdateService',
      );
      return false;
    }

    try {
      final uri = Uri.parse(appStoreUrl);

      AppLogger.info(
        'Opening App Store for update: $appStoreUrl',
        category: 'IosUpdateService',
      );

      final canLaunch = await canLaunchUrl(uri);

      if (!canLaunch) {
        AppLogger.warning(
          'Cannot launch App Store URL',
          category: 'IosUpdateService',
          data: {'url': appStoreUrl},
        );
        return false;
      }

      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );

      if (launched) {
        AppLogger.info(
          'Successfully opened App Store',
          category: 'IosUpdateService',
        );
      } else {
        AppLogger.warning(
          'Failed to open App Store',
          category: 'IosUpdateService',
        );
      }

      return launched;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Error opening App Store',
        error: e,
        stackTrace: stackTrace,
        category: 'IosUpdateService',
      );
      return false;
    }
  }
}
