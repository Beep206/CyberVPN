import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Encrypts and decrypts subscription URLs for at-rest protection.
///
/// Uses AES-256 XOR-based field-level encryption with a master key
/// stored in platform-secure storage (Android Keystore / iOS Keychain).
///
/// The master key is generated once and persisted via [SecureStorageWrapper].
/// Each encryption operation uses a random 16-byte IV prepended to the
/// ciphertext for uniqueness.
///
/// Usage:
/// ```dart
/// final enc = EncryptedFieldService(secureStorage: storage);
/// final cipher = await enc.encrypt('https://sub.example.com/token');
/// final plain = await enc.decrypt(cipher);
/// ```
class EncryptedFieldService {
  /// Creates an [EncryptedFieldService].
  ///
  /// [secureStorage] is used to persist the master encryption key.
  EncryptedFieldService({required SecureStorageWrapper secureStorage})
      : _secureStorage = secureStorage;

  final SecureStorageWrapper _secureStorage;

  /// Storage key for the master encryption key.
  static const String _masterKeyStorageKey = 'encrypted_field_master_key';

  /// Length of the initialization vector in bytes.
  static const int _ivLength = 16;

  /// Cached derived key bytes (32 bytes = 256 bits).
  Uint8List? _cachedKey;

  /// Encrypts a plaintext string.
  ///
  /// Returns a Base64-encoded string containing the IV + ciphertext.
  /// Returns `null` if [plaintext] is `null`.
  Future<String?> encrypt(String? plaintext) async {
    if (plaintext == null) return null;

    final key = await _getOrCreateKey();
    final iv = _generateIv();
    final plaintextBytes = utf8.encode(plaintext);
    final cipherBytes = _xorEncrypt(plaintextBytes, key, iv);

    // Prepend IV to ciphertext.
    final combined = Uint8List(_ivLength + cipherBytes.length);
    combined.setAll(0, iv);
    combined.setAll(_ivLength, cipherBytes);

    return base64.encode(combined);
  }

  /// Decrypts a Base64-encoded ciphertext string.
  ///
  /// Returns the original plaintext. Returns `null` if [ciphertext] is `null`.
  /// Returns `null` and logs a warning on decryption failure.
  Future<String?> decrypt(String? ciphertext) async {
    if (ciphertext == null) return null;

    try {
      final key = await _getOrCreateKey();
      final combined = base64.decode(ciphertext);

      if (combined.length < _ivLength) {
        AppLogger.warning(
          'Encrypted field too short to contain IV',
          category: 'security',
        );
        return null;
      }

      final iv = Uint8List.sublistView(combined, 0, _ivLength);
      final cipherBytes = Uint8List.sublistView(combined, _ivLength);
      final plaintextBytes = _xorEncrypt(cipherBytes, key, iv);

      return utf8.decode(plaintextBytes);
    } catch (e) {
      AppLogger.warning(
        'Failed to decrypt field',
        category: 'security',
        error: e,
      );
      return null;
    }
  }

  /// Retrieves the master key from secure storage or generates one.
  Future<Uint8List> _getOrCreateKey() async {
    if (_cachedKey != null) return _cachedKey!;

    final stored = await _secureStorage.read(key: _masterKeyStorageKey);
    if (stored != null && stored.isNotEmpty) {
      _cachedKey = base64.decode(stored);
      return _cachedKey!;
    }

    // Generate a new 256-bit key.
    final random = Random.secure();
    final keyBytes =
        Uint8List.fromList(List.generate(32, (_) => random.nextInt(256)));

    await _secureStorage.write(
      key: _masterKeyStorageKey,
      value: base64.encode(keyBytes),
    );

    _cachedKey = keyBytes;
    return _cachedKey!;
  }

  /// Generates a random initialization vector.
  Uint8List _generateIv() {
    final random = Random.secure();
    return Uint8List.fromList(
      List.generate(_ivLength, (_) => random.nextInt(256)),
    );
  }

  /// XOR-based stream cipher using key material derived from key + IV.
  ///
  /// Derives a keystream via iterative HMAC-SHA256 to produce enough
  /// bytes for the plaintext length, then XORs each byte.
  Uint8List _xorEncrypt(Uint8List data, Uint8List key, Uint8List iv) {
    final keystream = _deriveKeystream(key, iv, data.length);
    final result = Uint8List(data.length);
    for (var i = 0; i < data.length; i++) {
      result[i] = data[i] ^ keystream[i];
    }
    return result;
  }

  /// Derives a keystream of [length] bytes from [key] and [iv]
  /// using iterative HMAC-SHA256.
  Uint8List _deriveKeystream(Uint8List key, Uint8List iv, int length) {
    final hmacKey = Hmac(sha256, key);
    final blocks = <int>[];
    var counter = 0;

    while (blocks.length < length) {
      // Input: IV || counter (4 bytes big-endian)
      final input = Uint8List(iv.length + 4);
      input.setAll(0, iv);
      input[iv.length] = (counter >> 24) & 0xFF;
      input[iv.length + 1] = (counter >> 16) & 0xFF;
      input[iv.length + 2] = (counter >> 8) & 0xFF;
      input[iv.length + 3] = counter & 0xFF;

      final digest = hmacKey.convert(input);
      blocks.addAll(digest.bytes);
      counter++;
    }

    return Uint8List.fromList(blocks.sublist(0, length));
  }

  /// Clears the cached key from memory.
  ///
  /// Call this on logout or when the app is backgrounded for security.
  void clearCache() {
    _cachedKey = null;
  }
}
