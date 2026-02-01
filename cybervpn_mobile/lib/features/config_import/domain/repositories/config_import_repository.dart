import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';

/// Repository interface for managing imported VPN configurations
abstract class ConfigImportRepository {
  /// Import a VPN configuration from a URI string
  ///
  /// Parses the URI and saves the configuration
  /// Returns the imported configuration or throws an exception
  Future<ImportedConfig> importFromUri(String uri, ImportSource source);

  /// Import VPN configurations from a subscription URL
  ///
  /// Downloads and parses multiple configurations from the URL
  /// Returns a list of imported configurations
  Future<List<ImportedConfig>> importFromSubscriptionUrl(String url);

  /// Get all imported configurations
  ///
  /// Returns a list of all saved custom server configurations
  Future<List<ImportedConfig>> getImportedConfigs();

  /// Delete a specific configuration by ID
  ///
  /// Removes the configuration from storage
  Future<void> deleteConfig(String id);

  /// Delete all imported configurations
  ///
  /// Removes all custom server configurations from storage
  Future<void> deleteAll();

  /// Test connection to a specific configuration
  ///
  /// Attempts to connect to the server and updates reachability status
  /// Returns true if the server is reachable
  Future<bool> testConnection(String id);
}
