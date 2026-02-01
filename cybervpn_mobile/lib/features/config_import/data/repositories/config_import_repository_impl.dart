import 'dart:convert';
import 'dart:io';

import 'package:cybervpn_mobile/features/config_import/data/parsers/subscription_url_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/parsed_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Concrete implementation of [ConfigImportRepository] backed by
/// [SharedPreferences].
///
/// Stores imported VPN configurations as a JSON list under a single key.
/// Uses [ParseVpnUri] for single URI parsing and [SubscriptionUrlParser]
/// for fetching and parsing subscription URLs.
class ConfigImportRepositoryImpl implements ConfigImportRepository {
  ConfigImportRepositoryImpl({
    required SharedPreferences sharedPreferences,
    required SubscriptionUrlParser subscriptionUrlParser,
    ParseVpnUri? parseVpnUri,
  })  : _prefs = sharedPreferences,
        _subscriptionUrlParser = subscriptionUrlParser,
        _parseVpnUri = parseVpnUri ?? ParseVpnUri();

  final SharedPreferences _prefs;
  final SubscriptionUrlParser _subscriptionUrlParser;
  final ParseVpnUri _parseVpnUri;

  // ---------------------------------------------------------------------------
  // SharedPreferences key constants
  // ---------------------------------------------------------------------------

  /// Key for the JSON-encoded list of imported configurations.
  static const _kImportedConfigs = 'config_import.imported_configs';

  /// Key for the JSON-encoded map of subscription URL metadata.
  ///
  /// Structure: `{ url: lastRefreshTimestamp (ISO 8601) }`
  static const _kSubscriptionMeta = 'config_import.subscription_meta';

  /// Duration after which a subscription should be refreshed.
  static const _subscriptionRefreshInterval = Duration(hours: 24);

  /// Timeout for TCP connection tests.
  static const _connectionTestTimeout = Duration(seconds: 5);

  // ---------------------------------------------------------------------------
  // ConfigImportRepository implementation
  // ---------------------------------------------------------------------------

  @override
  Future<ImportedConfig> importFromUri(String uri, ImportSource source) async {
    final result = _parseVpnUri.call(uri);

    switch (result) {
      case ParseSuccess(:final config):
        final imported = _toImportedConfig(
          config: config,
          rawUri: uri,
          source: source,
        );

        final existing = await getImportedConfigs();
        // Avoid duplicates by checking for same raw URI
        final deduped = existing.where((c) => c.rawUri != uri).toList();
        deduped.add(imported);
        await _saveConfigs(deduped);

        return imported;

      case ParseFailure(:final message):
        throw ConfigImportException(
          message: 'Failed to parse URI: $message',
          uri: uri,
        );
    }
  }

  @override
  Future<List<ImportedConfig>> importFromSubscriptionUrl(String url) async {
    final parseResult = await _subscriptionUrlParser.parse(url);

    if (parseResult.isFailure) {
      final errorMessages =
          parseResult.errors.map((e) => e.toString()).join('; ');
      throw ConfigImportException(
        message: 'No valid configs found in subscription: $errorMessages',
        uri: url,
      );
    }

    final newConfigs = parseResult.configs;

    // Merge with existing configs, deduplicating by raw URI
    final existing = await getImportedConfigs();
    final existingUris = existing.map((c) => c.rawUri).toSet();
    final toAdd =
        newConfigs.where((c) => !existingUris.contains(c.rawUri)).toList();
    final merged = [...existing, ...toAdd];
    await _saveConfigs(merged);

    // Update subscription metadata with current timestamp
    await _updateSubscriptionMeta(url);

    return toAdd.isEmpty ? newConfigs : toAdd;
  }

  @override
  Future<List<ImportedConfig>> getImportedConfigs() async {
    final jsonString = _prefs.getString(_kImportedConfigs);
    if (jsonString == null || jsonString.isEmpty) {
      return [];
    }

    try {
      final List<dynamic> jsonList =
          json.decode(jsonString) as List<dynamic>;
      return jsonList
          .map((e) => _importedConfigFromJson(e as Map<String, dynamic>))
          .toList();
    } on FormatException {
      // Corrupted data — return empty list and clear storage
      await _prefs.remove(_kImportedConfigs);
      return [];
    }
  }

  @override
  Future<void> deleteConfig(String id) async {
    final configs = await getImportedConfigs();
    final filtered = configs.where((c) => c.id != id).toList();
    await _saveConfigs(filtered);
  }

  @override
  Future<void> deleteAll() async {
    await _prefs.remove(_kImportedConfigs);
    await _prefs.remove(_kSubscriptionMeta);
  }

  @override
  Future<bool> testConnection(String id) async {
    final configs = await getImportedConfigs();
    final config = configs.where((c) => c.id == id).firstOrNull;

    if (config == null) {
      throw ConfigImportException(
        message: 'Configuration not found',
        uri: id,
      );
    }

    try {
      final socket = await Socket.connect(
        config.serverAddress,
        config.port,
        timeout: _connectionTestTimeout,
      );
      await socket.close();

      // Update the config with test result
      await _updateConfigTestResult(id, isReachable: true);
      return true;
    } on SocketException {
      await _updateConfigTestResult(id, isReachable: false);
      return false;
    } on OSError {
      await _updateConfigTestResult(id, isReachable: false);
      return false;
    }
  }

  // ---------------------------------------------------------------------------
  // Subscription refresh logic
  // ---------------------------------------------------------------------------

  /// Refresh all subscription URLs that are older than 24 hours.
  ///
  /// Returns the number of subscriptions that were refreshed.
  Future<int> refreshStaleSubscriptions() async {
    final meta = _getSubscriptionMeta();
    var refreshed = 0;

    for (final entry in meta.entries) {
      final url = entry.key;
      final lastRefresh = DateTime.tryParse(entry.value);

      if (lastRefresh == null ||
          DateTime.now().difference(lastRefresh) >=
              _subscriptionRefreshInterval) {
        try {
          await _refreshSubscription(url);
          refreshed++;
        } on Exception {
          // Skip failed refreshes — will retry on next check
        }
      }
    }

    return refreshed;
  }

  /// Check if a subscription URL needs refreshing (24h elapsed).
  bool shouldRefreshSubscription(String url) {
    final meta = _getSubscriptionMeta();
    final lastRefreshStr = meta[url];
    if (lastRefreshStr == null) return true;

    final lastRefresh = DateTime.tryParse(lastRefreshStr);
    if (lastRefresh == null) return true;

    return DateTime.now().difference(lastRefresh) >=
        _subscriptionRefreshInterval;
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /// Save the full list of configs to SharedPreferences as JSON.
  Future<void> _saveConfigs(List<ImportedConfig> configs) async {
    final jsonList = configs.map(_importedConfigToJson).toList();
    await _prefs.setString(_kImportedConfigs, json.encode(jsonList));
  }

  /// Update the test result for a specific config.
  Future<void> _updateConfigTestResult(
    String id, {
    required bool isReachable,
  }) async {
    final configs = await getImportedConfigs();
    final updated = configs.map((c) {
      if (c.id == id) {
        return c.copyWith(
          isReachable: isReachable,
          lastTestedAt: DateTime.now(),
        );
      }
      return c;
    }).toList();
    await _saveConfigs(updated);
  }

  /// Refresh a single subscription URL and merge new configs.
  Future<void> _refreshSubscription(String url) async {
    final parseResult = await _subscriptionUrlParser.parse(url);
    if (parseResult.isFailure) return;

    final existing = await getImportedConfigs();

    // Remove old configs from this subscription, replace with fresh ones
    final withoutOld =
        existing.where((c) => c.subscriptionUrl != url).toList();
    final merged = [...withoutOld, ...parseResult.configs];
    await _saveConfigs(merged);
    await _updateSubscriptionMeta(url);
  }

  /// Read subscription metadata from SharedPreferences.
  Map<String, String> _getSubscriptionMeta() {
    final jsonString = _prefs.getString(_kSubscriptionMeta);
    if (jsonString == null || jsonString.isEmpty) return {};

    try {
      final Map<String, dynamic> decoded =
          json.decode(jsonString) as Map<String, dynamic>;
      return decoded.map((k, v) => MapEntry(k, v.toString()));
    } on FormatException {
      return {};
    }
  }

  /// Update the last-refresh timestamp for a subscription URL.
  Future<void> _updateSubscriptionMeta(String url) async {
    final meta = _getSubscriptionMeta();
    meta[url] = DateTime.now().toIso8601String();
    await _prefs.setString(_kSubscriptionMeta, json.encode(meta));
  }

  /// Convert a [ParsedConfig] to an [ImportedConfig].
  ImportedConfig _toImportedConfig({
    required ParsedConfig config,
    required String rawUri,
    required ImportSource source,
  }) {
    return ImportedConfig(
      id: _generateId(rawUri),
      name: config.remark ?? '${config.protocol}:${config.serverAddress}',
      rawUri: rawUri,
      protocol: config.protocol,
      serverAddress: config.serverAddress,
      port: config.port,
      source: source,
      importedAt: DateTime.now(),
    );
  }

  /// Generate a deterministic ID from the raw URI for deduplication.
  ///
  /// Uses FNV-1a hash, matching the approach in [SubscriptionUrlParser].
  String _generateId(String rawUri) {
    final bytes = utf8.encode(rawUri);
    var hash = 0xcbf29ce484222325;
    for (final byte in bytes) {
      hash ^= byte;
      hash = (hash * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF;
    }
    return hash.toRadixString(16).padLeft(16, '0');
  }

  // ---------------------------------------------------------------------------
  // JSON serialization helpers for ImportedConfig
  // ---------------------------------------------------------------------------

  /// Serialize an [ImportedConfig] to a JSON-compatible map.
  static Map<String, dynamic> _importedConfigToJson(ImportedConfig config) {
    return {
      'id': config.id,
      'name': config.name,
      'rawUri': config.rawUri,
      'protocol': config.protocol,
      'serverAddress': config.serverAddress,
      'port': config.port,
      'source': config.source.name,
      'subscriptionUrl': config.subscriptionUrl,
      'importedAt': config.importedAt.toIso8601String(),
      'lastTestedAt': config.lastTestedAt?.toIso8601String(),
      'isReachable': config.isReachable,
    };
  }

  /// Deserialize an [ImportedConfig] from a JSON map.
  static ImportedConfig _importedConfigFromJson(Map<String, dynamic> json) {
    return ImportedConfig(
      id: json['id'] as String,
      name: json['name'] as String,
      rawUri: json['rawUri'] as String,
      protocol: json['protocol'] as String,
      serverAddress: json['serverAddress'] as String,
      port: json['port'] as int,
      source: ImportSource.values.firstWhere(
        (e) => e.name == json['source'],
        orElse: () => ImportSource.manual,
      ),
      subscriptionUrl: json['subscriptionUrl'] as String?,
      importedAt: DateTime.parse(json['importedAt'] as String),
      lastTestedAt: json['lastTestedAt'] != null
          ? DateTime.parse(json['lastTestedAt'] as String)
          : null,
      isReachable: json['isReachable'] as bool?,
    );
  }
}

/// Exception thrown when a config import operation fails.
class ConfigImportException implements Exception {
  const ConfigImportException({
    required this.message,
    this.uri,
    this.cause,
  });

  /// Human-readable error description.
  final String message;

  /// The URI or URL that caused the error, if applicable.
  final String? uri;

  /// The underlying exception, if any.
  final Object? cause;

  @override
  String toString() {
    final uriPart = uri != null ? ' (URI: $uri)' : '';
    return 'ConfigImportException: $message$uriPart';
  }
}
