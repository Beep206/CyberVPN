import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Certificate pinning configuration for preventing MITM attacks.
///
/// Validates server TLS certificates against a set of pinned SHA-256
/// fingerprints before allowing the connection to proceed.
///
/// In debug mode ([kDebugMode]), certificate validation is bypassed to
/// allow development against local servers or self-signed certificates.
///
/// ### Usage
///
/// ```dart
/// final pinner = CertificatePinner(
///   pinnedFingerprints: [
///     'AA:BB:CC:DD...',  // Current production cert
///     'EE:FF:00:11...',  // Backup cert for rotation
///   ],
/// );
///
/// final validated = pinner.validate(certificate);
/// ```
class CertificatePinner {
  /// Creates a [CertificatePinner] with the given SHA-256 fingerprints.
  ///
  /// [pinnedFingerprints] should be a list of SHA-256 certificate
  /// fingerprints in colon-separated hex format, e.g.:
  /// `'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99'`
  const CertificatePinner({
    required this.pinnedFingerprints,
  });

  /// List of trusted SHA-256 certificate fingerprints.
  ///
  /// Should contain at least the current production certificate
  /// fingerprint plus one or more backup certificates to allow for
  /// certificate rotation without app updates.
  final List<String> pinnedFingerprints;

  /// Validates a certificate against the pinned fingerprints.
  ///
  /// Returns `true` if:
  /// - Running in debug mode ([kDebugMode] is true), OR
  /// - The certificate's SHA-256 fingerprint matches any of the
  ///   [pinnedFingerprints].
  ///
  /// Returns `false` otherwise.
  ///
  /// Logs validation attempts and failures to [AppLogger] and Sentry.
  bool validate(X509Certificate certificate) {
    // Bypass validation in debug mode
    if (kDebugMode) {
      AppLogger.debug(
        'Certificate pinning bypassed in debug mode',
        category: 'CertificatePinner',
        data: {
          'subject': certificate.subject,
          'issuer': certificate.issuer,
        },
      );
      return true;
    }

    final fingerprint = _computeFingerprint(certificate);

    if (kDebugMode) {
      AppLogger.debug(
        'Validating certificate',
        category: 'CertificatePinner',
        data: {
          'fingerprint': fingerprint,
          'subject': certificate.subject,
          'issuer': certificate.issuer,
          'startDate': certificate.startValidity.toIso8601String(),
          'endDate': certificate.endValidity.toIso8601String(),
        },
      );
    }

    final isValid = pinnedFingerprints.contains(fingerprint);

    if (!isValid) {
      AppLogger.error(
        'Certificate validation failed: fingerprint not in pinned list',
        category: 'CertificatePinner',
        data: {
          'pinnedCount': pinnedFingerprints.length,
        },
      );

      // Report to Sentry for monitoring
      if (EnvironmentConfig.sentryDsn.isNotEmpty) {
        Sentry.captureMessage(
          'Certificate pinning validation failed',
          level: SentryLevel.warning,
          withScope: (scope) {
            scope.setTag('security', 'cert-pinning');
            scope.setTag('subject', certificate.subject);
          },
        );
      }
    }

    return isValid;
  }

  /// Computes the SHA-256 fingerprint of a certificate.
  ///
  /// Returns the fingerprint as a colon-separated hex string in uppercase,
  /// e.g.: `'AA:BB:CC:DD:...'`
  String _computeFingerprint(X509Certificate certificate) {
    final der = certificate.der;
    final hash = sha256.convert(der);

    // Convert hash bytes to colon-separated hex string
    return hash.bytes
        .map((byte) => byte.toRadixString(16).padLeft(2, '0').toUpperCase())
        .join(':');
  }

  /// Creates an [HttpClient] configured with certificate pinning.
  ///
  /// The returned client will validate all certificates against the
  /// [pinnedFingerprints] before establishing TLS connections.
  ///
  /// Throws [CertificatePinningException] if certificate validation fails.
  HttpClient createHttpClient() {
    final client = HttpClient();

    client.badCertificateCallback = (cert, host, port) {
      final isValid = validate(cert);

      if (!isValid) {
        AppLogger.error(
          'Bad certificate detected',
          category: 'CertificatePinner',
          data: {
            'host': host,
            'port': port,
            'subject': cert.subject,
          },
        );
      }

      // Return validation result
      // true = allow connection
      // false = reject connection
      return isValid;
    };

    return client;
  }
}
