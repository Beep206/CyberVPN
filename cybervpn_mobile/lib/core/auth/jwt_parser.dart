import 'dart:convert';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// JWT payload with expiry information.
class JwtPayload {
  /// Unix timestamp when the token expires.
  final int exp;

  /// Unix timestamp when the token was issued.
  final int? iat;

  /// Subject (typically user ID).
  final String? sub;

  /// Token type (access or refresh).
  final String? type;

  const JwtPayload({
    required this.exp,
    this.iat,
    this.sub,
    this.type,
  });

  /// Returns the DateTime when this token expires.
  DateTime get expiresAt => DateTime.fromMillisecondsSinceEpoch(exp * 1000);

  /// Returns true if this token is expired.
  bool get isExpired => DateTime.now().isAfter(expiresAt);

  /// Returns the duration until this token expires.
  /// Negative duration means the token is already expired.
  Duration get timeUntilExpiry => expiresAt.difference(DateTime.now());
}

/// Parses JWT tokens to extract payload claims.
///
/// Note: This only decodes the payload - it does NOT verify the signature.
/// Signature verification should be done server-side.
class JwtParser {
  const JwtParser._();

  /// Parses a JWT access token and extracts the payload.
  ///
  /// Returns null if the token is malformed or cannot be parsed.
  static JwtPayload? parse(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) {
        return null;
      }

      // Decode the payload (second part)
      final payload = _decodeBase64Url(parts[1]);
      if (payload == null) {
        return null;
      }

      final json = jsonDecode(payload) as Map<String, dynamic>;

      final exp = json['exp'];
      if (exp is! int) {
        return null;
      }

      return JwtPayload(
        exp: exp,
        iat: json['iat'] as int?,
        sub: json['sub'] as String?,
        type: json['type'] as String?,
      );
    } catch (e) {
      AppLogger.warning('JWT parse failed', error: e, category: 'auth');
      return null;
    }
  }

  /// Decodes a base64url encoded string.
  static String? _decodeBase64Url(String input) {
    try {
      // Add padding if needed
      var normalized = input.replaceAll('-', '+').replaceAll('_', '/');
      switch (normalized.length % 4) {
        case 0:
          break;
        case 2:
          normalized += '==';
          break;
        case 3:
          normalized += '=';
          break;
        default:
          return null;
      }
      return utf8.decode(base64.decode(normalized));
    } catch (e) {
      AppLogger.warning('Base64 decode failed', error: e, category: 'auth');
      return null;
    }
  }
}
