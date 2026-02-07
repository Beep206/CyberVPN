import 'dart:io' show Platform;
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Attestation result
// ---------------------------------------------------------------------------

/// Result of an attestation attempt.
enum AttestationStatus {
  /// Token was generated successfully.
  success,

  /// Platform or device doesn't support attestation.
  unsupported,

  /// Attestation failed (network, server error, etc.).
  failed,

  /// Feature is disabled (e.g., debug builds).
  disabled,
}

/// Contains the result of an attestation attempt along with metadata.
class AttestationResult {
  const AttestationResult({
    required this.status,
    this.token,
    this.errorMessage,
    this.platform,
    this.deviceSupportsAttestation,
  });

  /// Status of the attestation attempt.
  final AttestationStatus status;

  /// The attestation token if successful.
  final String? token;

  /// Error message if failed.
  final String? errorMessage;

  /// Platform that generated the token.
  final String? platform;

  /// Whether the device supports attestation.
  final bool? deviceSupportsAttestation;

  Map<String, dynamic> toJson() => {
        'status': status.name,
        'hasToken': token != null,
        'platform': platform,
        'deviceSupportsAttestation': deviceSupportsAttestation,
        if (errorMessage != null) 'error': errorMessage,
      };
}

// ---------------------------------------------------------------------------
// Attestation trigger context
// ---------------------------------------------------------------------------

/// Context for when attestation is triggered.
enum AttestationTrigger {
  /// User login attempt.
  login,

  /// User registration attempt.
  registration,

  /// Purchase/subscription flow.
  purchase,

  /// App launch (optional background check).
  appLaunch,

  /// Manual trigger (e.g., debug screen).
  manual,
}

// ---------------------------------------------------------------------------
// App Attestation Service
// ---------------------------------------------------------------------------

/// Service for generating and logging app attestation tokens.
///
/// Implements Play Integrity (Android) and App Attest (iOS) in logging-only mode.
/// This service:
/// - Never blocks the user flow on attestation failure
/// - Logs all results to analytics and Sentry for monitoring
/// - Gracefully handles unsupported devices
///
/// Phase-in strategy:
/// 1. Logging mode (current): Generate tokens, log results, never enforce
/// 2. Soft enforcement: Warn on failure but allow flow to continue
/// 3. Hard enforcement: Block suspicious requests (future)
///
/// Platform requirements:
/// - Android: Play Integrity API (requires Google Play Services)
/// - iOS: App Attest (iOS 14.0+)
class AppAttestationService {
  AppAttestationService({
    required AnalyticsService analytics,
    this.enforceAttestation = false,
  }) : _analytics = analytics;

  final AnalyticsService _analytics;

  /// Whether to enforce attestation (block on failure).
  /// Currently always false (logging-only mode).
  final bool enforceAttestation;

  /// Whether attestation is supported on this device.
  bool get isSupported {
    if (kDebugMode) {
      // Skip in debug mode
      return false;
    }
    if (kIsWeb) {
      return false;
    }
    try {
      if (Platform.isAndroid) {
        // Android requires Play Services which is checked at runtime
        return true;
      }
      if (Platform.isIOS) {
        // iOS 14.0+ required for App Attest
        // Version check happens in native code
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  /// Generates an attestation token for the given trigger context.
  ///
  /// Returns an [AttestationResult] with the token or error information.
  /// This method never throws - all errors are captured in the result.
  ///
  /// [trigger] indicates why attestation is being requested (for logging).
  /// [challenge] is an optional server-provided nonce for replay protection.
  Future<AttestationResult> generateToken({
    required AttestationTrigger trigger,
    String? challenge,
  }) async {
    AppLogger.info(
      'Attestation requested: trigger=${trigger.name}',
      category: 'security.attestation',
    );

    // Check if attestation is disabled
    if (kDebugMode) {
      final result = AttestationResult(
        status: AttestationStatus.disabled,
        platform: _getPlatformName(),
        deviceSupportsAttestation: false,
      );
      await _logResult(result, trigger);
      return result;
    }

    // Check platform support
    if (!isSupported) {
      final result = AttestationResult(
        status: AttestationStatus.unsupported,
        platform: _getPlatformName(),
        deviceSupportsAttestation: false,
      );
      await _logResult(result, trigger);
      return result;
    }

    try {
      // Generate the attestation token
      final token = await _generatePlatformToken(challenge);

      final result = AttestationResult(
        status: AttestationStatus.success,
        token: token,
        platform: _getPlatformName(),
        deviceSupportsAttestation: true,
      );
      await _logResult(result, trigger);
      return result;
    } catch (e, st) {
      AppLogger.error(
        'Attestation token generation failed',
        error: e,
        stackTrace: st,
        category: 'security.attestation',
      );

      final result = AttestationResult(
        status: AttestationStatus.failed,
        errorMessage: e.toString(),
        platform: _getPlatformName(),
        deviceSupportsAttestation: true,
      );
      await _logResult(result, trigger);
      return result;
    }
  }

  /// Platform-specific token generation.
  ///
  /// In the current logging-only mode, this generates a placeholder token.
  /// For production enforcement, integrate with:
  /// - Android: google_play_integrity or app_attest_integrity package
  /// - iOS: app_attest or app_attest_integrity package
  Future<String> _generatePlatformToken(String? challenge) async {
    // TODO: Implement actual platform attestation
    // For now, generate a placeholder for logging infrastructure testing
    //
    // Real implementation would use:
    // Android: PlayIntegrity.requestIntegrityToken(challenge)
    // iOS: DCAppAttestService.generateAssertion(challenge)

    try {
      if (Platform.isAndroid) {
        // Placeholder for Play Integrity
        return 'android_placeholder_${DateTime.now().millisecondsSinceEpoch}';
      }
      if (Platform.isIOS) {
        // Placeholder for App Attest
        return 'ios_placeholder_${DateTime.now().millisecondsSinceEpoch}';
      }
      throw UnsupportedError('Platform not supported');
    } catch (e) {
      // Platform not available (e.g., tests)
      throw UnsupportedError('Platform check failed: $e');
    }
  }

  /// Logs the attestation result to analytics and Sentry.
  Future<void> _logResult(
    AttestationResult result,
    AttestationTrigger trigger,
  ) async {
    // Log to analytics
    try {
      await _analytics.logEvent(
        'app_attestation',
        parameters: {
          'status': result.status.name,
          'trigger': trigger.name,
          'platform': result.platform ?? 'unknown',
          'device_supports': result.deviceSupportsAttestation ?? false,
          'has_token': result.token != null,
        },
      );
    } catch (e) {
      AppLogger.warning(
        'Failed to log attestation to analytics',
        error: e,
        category: 'security.attestation',
      );
    }

    // Log to Sentry for monitoring
    try {
      unawaited(Sentry.addBreadcrumb(
        Breadcrumb(
          category: 'security.attestation',
          message: 'Attestation ${result.status.name}',
          level: result.status == AttestationStatus.success
              ? SentryLevel.info
              : SentryLevel.warning,
          data: result.toJson(),
        ),
      ));

      // Report failures to Sentry for monitoring
      if (result.status == AttestationStatus.failed) {
        await Sentry.captureMessage(
          'App attestation failed: ${result.errorMessage}',
          level: SentryLevel.warning,
          params: [result.toJson()],
        );
      }
    } catch (e) {
      AppLogger.warning(
        'Failed to log attestation to Sentry',
        error: e,
        category: 'security.attestation',
      );
    }

    AppLogger.info(
      'Attestation result logged: ${result.status.name}',
      category: 'security.attestation',
    );
  }

  String _getPlatformName() {
    if (kIsWeb) return 'web';
    try {
      if (Platform.isAndroid) return 'android';
      if (Platform.isIOS) return 'ios';
      if (Platform.isMacOS) return 'macos';
      if (Platform.isWindows) return 'windows';
      if (Platform.isLinux) return 'linux';
      return 'unknown';
    } catch (e) {
      return 'unknown';
    }
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provides the [AppAttestationService] instance.
final appAttestationServiceProvider = Provider<AppAttestationService>((ref) {
  final analytics = ref.watch(analyticsProvider);
  return AppAttestationService(
    analytics: analytics,
    enforceAttestation: false, // Logging-only mode
  );
});
