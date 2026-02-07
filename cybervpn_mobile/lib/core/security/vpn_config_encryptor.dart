import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Encrypts/decrypts VPN configuration data at rest using a user-derived key.
///
/// Uses XOR-based stream cipher with HMAC-SHA256 for integrity verification.
/// The user-derived key is a SHA-256 hash of the user's device token + device ID,
/// ensuring configs are bound to both the user and device.
class VpnConfigEncryptor {
  /// Derives an encryption key from user-specific material.
  ///
  /// [deviceToken] and [deviceId] are combined and hashed with SHA-256
  /// to produce a 256-bit key.
  static Uint8List deriveKey(String deviceToken, String deviceId) {
    final combined = utf8.encode('$deviceToken:$deviceId:vpn_config_key');
    final hash = sha256.convert(combined);
    return Uint8List.fromList(hash.bytes);
  }

  /// Encrypts [plaintext] with the given [key].
  ///
  /// Returns a base64-encoded string containing: IV (16 bytes) + ciphertext.
  static String encrypt(String plaintext, Uint8List key) {
    final random = Random.secure();
    final iv = Uint8List.fromList(
      List<int>.generate(16, (_) => random.nextInt(256)),
    );

    final data = utf8.encode(plaintext);
    final keyStream = _expandKey(key, iv, data.length);
    final ciphertext = Uint8List(data.length);
    for (var i = 0; i < data.length; i++) {
      ciphertext[i] = data[i] ^ keyStream[i];
    }

    final result = Uint8List(iv.length + ciphertext.length);
    result.setAll(0, iv);
    result.setAll(iv.length, ciphertext);

    return base64Encode(result);
  }

  /// Decrypts a base64-encoded [ciphertext] with the given [key].
  ///
  /// Returns the original plaintext, or `null` if decryption fails.
  static String? decrypt(String ciphertext, Uint8List key) {
    try {
      final raw = base64Decode(ciphertext);
      if (raw.length < 16) return null;

      final iv = Uint8List.sublistView(raw, 0, 16);
      final data = Uint8List.sublistView(raw, 16);

      final keyStream = _expandKey(key, iv, data.length);
      final plainBytes = Uint8List(data.length);
      for (var i = 0; i < data.length; i++) {
        plainBytes[i] = data[i] ^ keyStream[i];
      }

      return utf8.decode(plainBytes);
    } catch (e) {
      AppLogger.warning('VPN config decryption failed', error: e, category: 'security');
      return null;
    }
  }

  /// Generates an HMAC-SHA256 signature for [data] using [key].
  static String sign(String data, Uint8List key) {
    final hmacSha256 = Hmac(sha256, key);
    final digest = hmacSha256.convert(utf8.encode(data));
    return digest.toString();
  }

  /// Verifies an HMAC-SHA256 [signature] for [data] using [key].
  static bool verify(String data, String signature, Uint8List key) {
    final expected = sign(data, key);
    // Constant-time comparison to prevent timing attacks.
    if (expected.length != signature.length) return false;
    var result = 0;
    for (var i = 0; i < expected.length; i++) {
      result |= expected.codeUnitAt(i) ^ signature.codeUnitAt(i);
    }
    return result == 0;
  }

  /// Expands [key] + [iv] into a keystream of [length] bytes using HMAC rounds.
  static Uint8List _expandKey(Uint8List key, Uint8List iv, int length) {
    final hmacInstance = Hmac(sha256, key);
    final stream = BytesBuilder();
    var counter = 0;

    while (stream.length < length) {
      final input = Uint8List(iv.length + 4);
      input.setAll(0, iv);
      input[iv.length] = (counter >> 24) & 0xFF;
      input[iv.length + 1] = (counter >> 16) & 0xFF;
      input[iv.length + 2] = (counter >> 8) & 0xFF;
      input[iv.length + 3] = counter & 0xFF;

      final block = hmacInstance.convert(input);
      stream.add(block.bytes);
      counter++;
    }

    return Uint8List.sublistView(stream.toBytes(), 0, length);
  }
}
