import 'dart:io';

import 'package:in_app_update/in_app_update.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Android-specific update service using Play Core API.
///
/// Supports:
/// - Flexible update flow (optional updates - background download)
/// - Immediate update flow (mandatory updates - blocks app)
class AndroidUpdateService {
  /// Checks if an update is available via Play Store.
  ///
  /// Returns [AppUpdateInfo] if available, null otherwise.
  Future<AppUpdateInfo?> checkForUpdate() async {
    if (!Platform.isAndroid) {
      AppLogger.warning(
        'AndroidUpdateService called on non-Android platform',
        category: 'AndroidUpdateService',
      );
      return null;
    }

    try {
      final updateInfo = await InAppUpdate.checkForUpdate();

      AppLogger.info(
        'Play Store update check: available=${updateInfo.updateAvailability}',
        category: 'AndroidUpdateService',
        data: {
          'update_available': updateInfo.updateAvailability.toString(),
          'immediate_allowed': updateInfo.immediateUpdateAllowed,
          'flexible_allowed': updateInfo.flexibleUpdateAllowed,
        },
      );

      return updateInfo;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to check for update via Play Store',
        error: e,
        stackTrace: stackTrace,
        category: 'AndroidUpdateService',
      );
      return null;
    }
  }

  /// Starts an immediate update flow (mandatory - blocks app until updated).
  ///
  /// Used for major version updates that require user to update immediately.
  /// The update UI is fullscreen and blocks all app interaction.
  ///
  /// Returns [AppUpdateResult] indicating the outcome.
  Future<AppUpdateResult> performImmediateUpdate() async {
    if (!Platform.isAndroid) {
      AppLogger.warning(
        'Immediate update called on non-Android platform',
        category: 'AndroidUpdateService',
      );
      return AppUpdateResult.inAppUpdateFailed;
    }

    try {
      AppLogger.info(
        'Starting immediate update flow',
        category: 'AndroidUpdateService',
      );

      final result = await InAppUpdate.performImmediateUpdate();

      AppLogger.info(
        'Immediate update result: $result',
        category: 'AndroidUpdateService',
      );

      return result;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Immediate update failed',
        error: e,
        stackTrace: stackTrace,
        category: 'AndroidUpdateService',
      );
      return AppUpdateResult.inAppUpdateFailed;
    }
  }

  /// Starts a flexible update flow (optional - background download).
  ///
  /// Used for minor/patch updates. User can continue using app while
  /// update downloads in background. Install is triggered later.
  ///
  /// Returns [AppUpdateResult] indicating the outcome.
  Future<AppUpdateResult> startFlexibleUpdate() async {
    if (!Platform.isAndroid) {
      AppLogger.warning(
        'Flexible update called on non-Android platform',
        category: 'AndroidUpdateService',
      );
      return AppUpdateResult.inAppUpdateFailed;
    }

    try {
      AppLogger.info(
        'Starting flexible update flow',
        category: 'AndroidUpdateService',
      );

      final result = await InAppUpdate.startFlexibleUpdate();

      AppLogger.info(
        'Flexible update started: $result',
        category: 'AndroidUpdateService',
      );

      return result;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Flexible update failed',
        error: e,
        stackTrace: stackTrace,
        category: 'AndroidUpdateService',
      );
      return AppUpdateResult.inAppUpdateFailed;
    }
  }

  /// Completes a flexible update (installs downloaded update).
  ///
  /// Should be called after [startFlexibleUpdate] when download completes.
  /// This will restart the app to apply the update.
  Future<void> completeFlexibleUpdate() async {
    if (!Platform.isAndroid) {
      AppLogger.warning(
        'Complete flexible update called on non-Android platform',
        category: 'AndroidUpdateService',
      );
      return;
    }

    try {
      AppLogger.info(
        'Completing flexible update (app will restart)',
        category: 'AndroidUpdateService',
      );

      await InAppUpdate.completeFlexibleUpdate();

      AppLogger.info(
        'Flexible update completed successfully',
        category: 'AndroidUpdateService',
      );
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to complete flexible update',
        error: e,
        stackTrace: stackTrace,
        category: 'AndroidUpdateService',
      );
    }
  }
}
