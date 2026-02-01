import 'dart:io';

import 'package:flutter/material.dart';
import 'package:in_app_update/in_app_update.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/shared/services/android_update_service.dart';
import 'package:cybervpn_mobile/shared/services/ios_update_service.dart';
import 'package:cybervpn_mobile/shared/services/version_service.dart';
import 'package:cybervpn_mobile/shared/widgets/in_app_update_dialog.dart';

/// Platform-agnostic update service.
///
/// Delegates to platform-specific implementations:
/// - Android: [AndroidUpdateService] (Play Core in-app updates)
/// - iOS: [IosUpdateService] (App Store redirect)
class PlatformUpdateService {
  final VersionService _versionService;
  final AndroidUpdateService _androidUpdateService;
  final IosUpdateService _iosUpdateService;
  final SharedPreferences _prefs;

  PlatformUpdateService({
    required VersionService versionService,
    required SharedPreferences prefs,
    AndroidUpdateService? androidUpdateService,
    IosUpdateService? iosUpdateService,
  })  : _versionService = versionService,
        _androidUpdateService = androidUpdateService ?? AndroidUpdateService(),
        _iosUpdateService = iosUpdateService ?? IosUpdateService(),
        _prefs = prefs;

  /// Checks for updates and shows dialog if needed.
  ///
  /// Should be called on app launch.
  /// Respects rate limiting (max once per hour) and snooze status.
  ///
  /// Returns `true` if update dialog was shown, `false` otherwise.
  Future<bool> checkAndShowUpdateDialog(BuildContext context) async {
    try {
      AppLogger.info(
        'Checking for app update on launch',
        category: 'PlatformUpdateService',
      );

      // Check version via backend
      final updateStatus = await _versionService.checkForUpdate();

      if (updateStatus == null) {
        AppLogger.debug(
          'No update check performed (rate limited or failed)',
          category: 'PlatformUpdateService',
        );
        return false;
      }

      if (!updateStatus.needsUpdate) {
        AppLogger.info(
          'App is up to date',
          category: 'PlatformUpdateService',
        );
        return false;
      }

      // Check if dialog should be shown (respects snooze)
      final shouldShow = InAppUpdateDialog.shouldShowDialog(
        updateInfo: updateStatus,
        prefs: _prefs,
      );

      if (!shouldShow) {
        AppLogger.debug(
          'Update available but dialog snoozed',
          category: 'PlatformUpdateService',
        );
        return false;
      }

      if (!context.mounted) return false;

      // Show update dialog
      await InAppUpdateDialog.show(
        context: context,
        updateInfo: updateStatus,
        onUpdate: () => _handleUpdate(context, updateStatus),
        prefs: _prefs,
        onDismiss: () => _handleDismiss(updateStatus),
      );

      return true;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Error in checkAndShowUpdateDialog',
        error: e,
        stackTrace: stackTrace,
        category: 'PlatformUpdateService',
      );
      return false;
    }
  }

  /// Handles update button press - triggers platform-specific update.
  Future<void> _handleUpdate(
    BuildContext context,
    UpdateStatus updateStatus,
  ) async {
    AppLogger.info(
      'User initiated update (mandatory: ${updateStatus.isMandatory})',
      category: 'PlatformUpdateService',
    );

    if (Platform.isAndroid) {
      await _performAndroidUpdate(updateStatus.isMandatory);
    } else if (Platform.isIOS) {
      await _performIosUpdate();
    } else {
      AppLogger.warning(
        'Update requested on unsupported platform',
        category: 'PlatformUpdateService',
      );
    }

    // Close dialog after initiating update
    if (context.mounted) {
      Navigator.of(context).pop();
    }
  }

  /// Performs Android-specific update using Play Core API.
  Future<void> _performAndroidUpdate(bool isMandatory) async {
    if (isMandatory) {
      // Immediate update for mandatory updates
      AppLogger.info(
        'Starting immediate update (mandatory)',
        category: 'PlatformUpdateService',
      );
      await _androidUpdateService.performImmediateUpdate();
    } else {
      // Flexible update for optional updates
      AppLogger.info(
        'Starting flexible update (optional)',
        category: 'PlatformUpdateService',
      );
      final result = await _androidUpdateService.startFlexibleUpdate();

      // Auto-complete flexible update when download finishes
      // In production, you might want to show a notification first
      if (result == AppUpdateResult.success) {
        await _androidUpdateService.completeFlexibleUpdate();
      }
    }
  }

  /// Performs iOS-specific update by opening App Store.
  Future<void> _performIosUpdate() async {
    AppLogger.info(
      'Opening App Store for update',
      category: 'PlatformUpdateService',
    );
    await _iosUpdateService.openAppStore();
  }

  /// Handles dialog dismissal (for optional updates).
  void _handleDismiss(UpdateStatus updateStatus) {
    AppLogger.info(
      'User dismissed update dialog',
      category: 'PlatformUpdateService',
      data: {
        'version': updateStatus.latestVersion,
        'mandatory': updateStatus.isMandatory,
      },
    );
  }
}
