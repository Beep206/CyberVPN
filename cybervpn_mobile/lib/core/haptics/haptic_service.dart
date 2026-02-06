import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Service for managing haptic feedback throughout the application.
///
/// Provides semantic methods for different types of tactile feedback:
/// * [selection] - Light tap for UI selections (buttons, toggles)
/// * [impact] - Medium impact for standard interactions
/// * [heavy] - Heavy impact for significant actions
/// * [success] - Success pattern (light → medium)
/// * [error] - Error feedback (heavy impact)
///
/// Respects user settings and platform capabilities. If haptics are disabled
/// in app settings or the platform doesn't support haptics, calls are no-ops.
///
/// Usage:
/// ```dart
/// final haptics = ref.read(hapticServiceProvider);
/// await haptics.selection(); // On button tap
/// await haptics.success();   // On successful operation
/// ```
class HapticService {
  /// Creates a [HapticService] instance.
  ///
  /// [ref] is used to access the settings repository to check if haptics
  /// are enabled. The enabled state is cached at construction to avoid
  /// async reads on every haptic call.
  HapticService(this._ref) {
    unawaited(_loadEnabledState());
  }

  final Ref _ref;

  /// Cached haptics-enabled state. Defaults to `true` until loaded.
  bool _cachedEnabled = true;

  /// Checks if haptics are supported on the current platform.
  bool get _isPlatformSupported {
    return Platform.isIOS || Platform.isAndroid;
  }

  /// Whether haptics are currently enabled (synchronous, cached).
  bool get isEnabled => _cachedEnabled;

  /// Loads the haptics-enabled state from settings repository.
  Future<void> _loadEnabledState() async {
    try {
      final settingsRepo = _ref.read(settingsRepositoryProvider);
      final result = await settingsRepo.getSettings();
      _cachedEnabled = switch (result) {
        Success(:final data) => data.hapticsEnabled,
        Failure() => true,
      };
    } catch (e, st) {
      AppLogger.warning(
        'Failed to check haptics setting, defaulting to enabled',
        error: e,
        stackTrace: st,
        category: 'haptics',
      );
      _cachedEnabled = true;
    }
  }

  /// Call after the user changes the haptics setting to update the cache.
  Future<void> refreshEnabledState() => _loadEnabledState();

  /// Triggers a selection haptic feedback.
  ///
  /// Use for UI selections like button taps, toggle switches, and
  /// radio button selections. Provides a light, subtle feedback.
  ///
  /// This is a no-op if haptics are disabled or unsupported.
  Future<void> selection() async {
    if (!_isPlatformSupported) return;
    if (!_cachedEnabled) return;

    try {
      await HapticFeedback.selectionClick();
    } catch (e, st) {
      AppLogger.warning(
        'Failed to trigger selection haptic',
        error: e,
        stackTrace: st,
        category: 'haptics',
      );
    }
  }

  /// Triggers a medium impact haptic feedback.
  ///
  /// Use for standard interactions that deserve tactile confirmation,
  /// such as navigation actions, card dismissals, or form submissions.
  ///
  /// This is a no-op if haptics are disabled or unsupported.
  Future<void> impact() async {
    if (!_isPlatformSupported) return;
    if (!_cachedEnabled) return;

    try {
      await HapticFeedback.mediumImpact();
    } catch (e, st) {
      AppLogger.warning(
        'Failed to trigger impact haptic',
        error: e,
        stackTrace: st,
        category: 'haptics',
      );
    }
  }

  /// Triggers a heavy impact haptic feedback.
  ///
  /// Use for significant actions like connecting/disconnecting VPN,
  /// deleting items, or confirming important operations.
  ///
  /// This is a no-op if haptics are disabled or unsupported.
  Future<void> heavy() async {
    if (!_isPlatformSupported) return;
    if (!_cachedEnabled) return;

    try {
      await HapticFeedback.heavyImpact();
    } catch (e, st) {
      AppLogger.warning(
        'Failed to trigger heavy haptic',
        error: e,
        stackTrace: st,
        category: 'haptics',
      );
    }
  }

  /// Triggers a success haptic pattern.
  ///
  /// Provides a light impact followed by a medium impact to create
  /// a distinctive "success" feel. Use for successful operations like
  /// completed payments, successful connections, or saved settings.
  ///
  /// This is a no-op if haptics are disabled or unsupported.
  Future<void> success() async {
    if (!_isPlatformSupported) return;
    if (!_cachedEnabled) return;

    try {
      // Create success pattern: light → delay → medium
      await HapticFeedback.lightImpact();
      await Future<void>.delayed(const Duration(milliseconds: 50));
      await HapticFeedback.mediumImpact();
    } catch (e, st) {
      AppLogger.warning(
        'Failed to trigger success haptic',
        error: e,
        stackTrace: st,
        category: 'haptics',
      );
    }
  }

  /// Triggers an error haptic feedback.
  ///
  /// Provides a heavy impact to signal an error or failed operation.
  /// Use for validation errors, network failures, or operation failures.
  ///
  /// This is a no-op if haptics are disabled or unsupported.
  Future<void> error() async {
    if (!_isPlatformSupported) return;
    if (!_cachedEnabled) return;

    try {
      await HapticFeedback.heavyImpact();
    } catch (e, st) {
      AppLogger.warning(
        'Failed to trigger error haptic',
        error: e,
        stackTrace: st,
        category: 'haptics',
      );
    }
  }
}

/// Provides the [HapticService] singleton instance.
///
/// Access haptic feedback throughout the app via this provider:
/// ```dart
/// final haptics = ref.read(hapticServiceProvider);
/// await haptics.selection();
/// ```
final hapticServiceProvider = Provider<HapticService>((ref) {
  return HapticService(ref);
});
