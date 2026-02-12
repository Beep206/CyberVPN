import 'dart:async';
import 'dart:io';

import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';

// ---------------------------------------------------------------------------
// Protocol Fallback Use-Case
// ---------------------------------------------------------------------------

/// Ordered fallback chain for VPN transport protocols.
///
/// When the primary protocol (Reality / VLESS) fails after [maxRetries]
/// attempts, the next protocol in the chain is tried until all options
/// are exhausted.
///
/// Protocols:
///  1. **Reality** (VLESS)  – primary
///  2. **XHTTP**  (VMess)  – first fallback
///  3. **WS-TLS** (Trojan) – second fallback
class ProtocolFallback {
  /// Maximum connection attempts per protocol before falling back.
  static const int maxRetries = 3;

  /// Timeout for the TCP handshake test.
  static const Duration handshakeTimeout = Duration(seconds: 5);

  /// Ordered list of protocols to attempt.
  static const List<VpnProtocol> _fallbackChain = [
    VpnProtocol.vless, // Reality
    VpnProtocol.vmess, // XHTTP
    VpnProtocol.trojan, // WS-TLS
  ];

  final SecureStorageWrapper _storage;

  // SENSITIVE: Preferred VPN protocol is a security setting - must use SecureStorage
  static const String _preferredProtocolKey = 'preferred_vpn_protocol';

  ProtocolFallback({required SecureStorageWrapper storage})
      : _storage = storage;

  // ── Public API ──────────────────────────────────────────────────────────

  /// Attempts to find a working protocol for the given [serverAddress] and
  /// [port].
  ///
  /// If [manualOverride] is non-null, only that protocol is tested (no
  /// fallback chain). If the override fails, a [ProtocolFallbackFailure]
  /// is returned.
  ///
  /// Returns the first protocol that passes the TCP handshake test.
  Future<ProtocolFallbackResult> execute({
    required String serverAddress,
    required int port,
    VpnProtocol? manualOverride,
  }) async {
    final chain =
        manualOverride != null ? [manualOverride] : await _buildChain();

    final log = <ProtocolAttemptLog>[];

    for (final protocol in chain) {
      for (int attempt = 1; attempt <= maxRetries; attempt++) {
        AppLogger.info(
          'Protocol fallback: testing ${protocol.name} '
          '(attempt $attempt/$maxRetries) -> $serverAddress:$port',
        );

        final success = await _testProtocol(serverAddress, port);

        log.add(ProtocolAttemptLog(
          protocol: protocol,
          attempt: attempt,
          success: success,
          timestamp: DateTime.now(),
        ));

        if (success) {
          AppLogger.info(
            'Protocol fallback: ${protocol.name} succeeded on attempt $attempt',
          );
          // Persist as preferred for next time.
          await _savePreferredProtocol(protocol);
          return ProtocolFallbackSuccess(
            protocol: protocol,
            attemptLog: log,
          );
        }

        AppLogger.warning(
          'Protocol fallback: ${protocol.name} attempt $attempt failed',
        );
      }

      AppLogger.warning(
        'Protocol fallback: ${protocol.name} exhausted $maxRetries retries',
      );
    }

    AppLogger.error('Protocol fallback: all protocols unavailable');
    return ProtocolFallbackFailure(
      message: 'All protocols unavailable',
      attemptLog: log,
    );
  }

  /// Stores the user's preferred protocol override.
  ///
  /// Pass `null` to clear the override and revert to automatic fallback.
  Future<void> setPreferredProtocol(VpnProtocol? protocol) async {
    if (protocol == null) {
      // SENSITIVE: Delete preferred protocol from SecureStorage
      await _storage.delete(key: _preferredProtocolKey);
      AppLogger.info('Protocol fallback: cleared preferred protocol');
    } else {
      // SENSITIVE: Store preferred protocol in SecureStorage (security-related setting)
      await _storage.write(key: _preferredProtocolKey, value: protocol.name);
      AppLogger.info(
        'Protocol fallback: set preferred protocol to ${protocol.name}',
      );
    }
  }

  /// Retrieves the user's preferred protocol, if set.
  Future<VpnProtocol?> getPreferredProtocol() async {
    // SENSITIVE: Read preferred protocol from SecureStorage
    final raw = await _storage.read(key: _preferredProtocolKey);
    if (raw == null) return null;
    return VpnProtocol.values.where((p) => p.name == raw).firstOrNull;
  }

  // ── Private helpers ─────────────────────────────────────────────────────

  /// Builds the protocol chain, placing the preferred protocol first
  /// (if one is stored).
  Future<List<VpnProtocol>> _buildChain() async {
    final preferred = await getPreferredProtocol();
    if (preferred == null) return _fallbackChain;

    // Move preferred to front, keep the rest in order.
    return [
      preferred,
      ..._fallbackChain.where((p) => p != preferred),
    ];
  }

  /// Performs a TCP handshake test to [address]:[port].
  ///
  /// Returns `true` if the socket connects within [handshakeTimeout].
  Future<bool> _testProtocol(String address, int port) async {
    Socket? socket;
    try {
      socket = await Socket.connect(
        address,
        port,
        timeout: handshakeTimeout,
      );
      return true;
    } on SocketException catch (e) {
      AppLogger.debug('TCP handshake failed: $e');
      return false;
    } on TimeoutException {
      AppLogger.debug('TCP handshake timed out');
      return false;
    } catch (e) {
      AppLogger.debug('TCP handshake unexpected error: $e');
      return false;
    } finally {
      try {
        socket?.destroy();
      } catch (_) { /* intentionally ignored */ }
    }
  }

  Future<void> _savePreferredProtocol(VpnProtocol protocol) async {
    try {
      // SENSITIVE: Persist successful protocol to SecureStorage
      await _storage.write(key: _preferredProtocolKey, value: protocol.name);
    } catch (e) {
      AppLogger.warning('Failed to save preferred protocol', error: e);
    }
  }
}

// ---------------------------------------------------------------------------
// Result types
// ---------------------------------------------------------------------------

/// Base result type for the protocol fallback operation.
@immutable
sealed class ProtocolFallbackResult {
  final List<ProtocolAttemptLog> attemptLog;

  const ProtocolFallbackResult({required this.attemptLog});

  bool get isSuccess => this is ProtocolFallbackSuccess;
  bool get isFailure => this is ProtocolFallbackFailure;
}

/// A protocol was successfully tested and can be used for connection.
class ProtocolFallbackSuccess extends ProtocolFallbackResult {
  final VpnProtocol protocol;

  const ProtocolFallbackSuccess({
    required this.protocol,
    required super.attemptLog,
  });
}

/// All protocols in the fallback chain failed.
class ProtocolFallbackFailure extends ProtocolFallbackResult {
  final String message;

  const ProtocolFallbackFailure({
    required this.message,
    required super.attemptLog,
  });
}

// ---------------------------------------------------------------------------
// Attempt log entry
// ---------------------------------------------------------------------------

/// Records a single connection test attempt for diagnostics.
class ProtocolAttemptLog {
  final VpnProtocol protocol;
  final int attempt;
  final bool success;
  final DateTime timestamp;

  const ProtocolAttemptLog({
    required this.protocol,
    required this.attempt,
    required this.success,
    required this.timestamp,
  });

  @override
  String toString() =>
      'ProtocolAttemptLog(${protocol.name}, attempt=$attempt, '
      'success=$success, $timestamp)';
}
