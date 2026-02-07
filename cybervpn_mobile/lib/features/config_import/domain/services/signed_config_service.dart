import 'dart:convert';
import 'dart:typed_data';

import 'package:cybervpn_mobile/core/security/vpn_config_encryptor.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Represents a signed VPN configuration with HMAC integrity verification.
///
/// Format: `cybervpn://signed?config=<base64>&sig=<hex-hmac>`
///
/// The signature is computed using HMAC-SHA256 with a shared key derived
/// from the user's device token and device ID, ensuring configs cannot be
/// tampered with after generation.
class SignedConfigService {
  /// Prefix for signed config URIs.
  static const String uriPrefix = 'cybervpn://signed';

  /// Creates a signed config URI from raw config data.
  ///
  /// [configJson] is the VPN configuration as a JSON string.
  /// [key] is the HMAC signing key (from VpnConfigEncryptor.deriveKey).
  static String createSignedUri(String configJson, Uint8List key) {
    final configBase64 = base64Encode(utf8.encode(configJson));
    final signature = VpnConfigEncryptor.sign(configBase64, key);
    return '$uriPrefix?config=$configBase64&sig=$signature';
  }

  /// Parses and verifies a signed config URI.
  ///
  /// Returns the decoded config JSON string if the signature is valid,
  /// or `null` if verification fails or the URI is malformed.
  static String? parseAndVerify(String uri, Uint8List key) {
    try {
      if (!uri.startsWith(uriPrefix)) {
        AppLogger.warning(
          'Not a signed config URI',
          category: 'config.signed',
        );
        return null;
      }

      final parsedUri = Uri.parse(uri);
      final configBase64 = parsedUri.queryParameters['config'];
      final signature = parsedUri.queryParameters['sig'];

      if (configBase64 == null || signature == null) {
        AppLogger.warning(
          'Signed config URI missing config or sig parameter',
          category: 'config.signed',
        );
        return null;
      }

      // Verify HMAC signature
      if (!VpnConfigEncryptor.verify(configBase64, signature, key)) {
        AppLogger.warning(
          'Signed config HMAC verification failed — config may be tampered',
          category: 'config.signed',
        );
        return null;
      }

      // Decode the config
      final configJson = utf8.decode(base64Decode(configBase64));
      AppLogger.info(
        'Signed config verified successfully',
        category: 'config.signed',
      );
      return configJson;
    } catch (e) {
      AppLogger.error(
        'Failed to parse signed config URI',
        error: e,
        category: 'config.signed',
      );
      return null;
    }
  }

  /// Checks if a URI is a signed config format.
  static bool isSignedConfig(String uri) => uri.startsWith(uriPrefix);
}
