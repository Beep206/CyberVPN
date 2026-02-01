import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Update status returned by [VersionService.checkForUpdate].
class UpdateStatus {
  /// Whether an update is available.
  final bool needsUpdate;

  /// Whether the update is mandatory (blocks app usage).
  final bool isMandatory;

  /// Current app version installed on device.
  final String currentVersion;

  /// Latest available version from backend.
  final String latestVersion;

  const UpdateStatus({
    required this.needsUpdate,
    required this.isMandatory,
    required this.currentVersion,
    required this.latestVersion,
  });

  @override
  String toString() => 'UpdateStatus('
      'needsUpdate: $needsUpdate, '
      'isMandatory: $isMandatory, '
      'current: $currentVersion, '
      'latest: $latestVersion)';
}

/// Service for checking app version and determining update requirements.
///
/// Responsibilities:
/// - Fetch current app version using PackageInfo
/// - Fetch latest version from backend API
/// - Compare versions using semantic versioning
/// - Determine update type (mandatory for major version diff, optional for minor)
/// - Rate-limit version checks (max once per hour)
class VersionService {
  final ApiClient _apiClient;
  final SharedPreferences _prefs;

  static const String _lastCheckKey = 'version_check_last_timestamp';
  static const Duration _checkInterval = Duration(hours: 1);

  VersionService({
    required ApiClient apiClient,
    required SharedPreferences prefs,
  })  : _apiClient = apiClient,
        _prefs = prefs;

  /// Checks if an update is available and returns update status.
  ///
  /// Returns `null` if:
  /// - Last check was less than 1 hour ago (rate limiting)
  /// - Failed to fetch version info
  ///
  /// Returns [UpdateStatus] with update details if check succeeds.
  Future<UpdateStatus?> checkForUpdate({bool force = false}) async {
    try {
      // Rate limiting: skip check if called within last hour (unless forced)
      if (!force && !_shouldCheckForUpdate()) {
        AppLogger.debug(
          'Skipping version check - last check was less than 1 hour ago',
          category: 'VersionService',
        );
        return null;
      }

      // Get current app version
      final currentVersion = await _getCurrentVersion();
      AppLogger.info(
        'Current app version: $currentVersion',
        category: 'VersionService',
      );

      // Fetch latest version from backend
      final latestVersion = await _fetchLatestVersion();
      if (latestVersion == null) {
        AppLogger.warning(
          'Failed to fetch latest version from backend',
          category: 'VersionService',
        );
        return null;
      }

      AppLogger.info(
        'Latest app version from backend: $latestVersion',
        category: 'VersionService',
      );

      // Update last check timestamp
      await _updateLastCheckTimestamp();

      // Compare versions and determine update type
      final comparison = _compareVersions(currentVersion, latestVersion);

      if (comparison == 0) {
        // Already on latest version
        return UpdateStatus(
          needsUpdate: false,
          isMandatory: false,
          currentVersion: currentVersion,
          latestVersion: latestVersion,
        );
      }

      if (comparison > 0) {
        // Current version is newer than backend version (dev/beta scenario)
        AppLogger.info(
          'Current version ($currentVersion) is newer than backend ($latestVersion)',
          category: 'VersionService',
        );
        return UpdateStatus(
          needsUpdate: false,
          isMandatory: false,
          currentVersion: currentVersion,
          latestVersion: latestVersion,
        );
      }

      // Update is available (comparison < 0)
      final isMandatory = _isMandatoryUpdate(currentVersion, latestVersion);

      AppLogger.info(
        'Update available: $currentVersion -> $latestVersion '
        '(${isMandatory ? 'MANDATORY' : 'optional'})',
        category: 'VersionService',
      );

      return UpdateStatus(
        needsUpdate: true,
        isMandatory: isMandatory,
        currentVersion: currentVersion,
        latestVersion: latestVersion,
      );
    } catch (e, stackTrace) {
      AppLogger.error(
        'Error checking for update',
        error: e,
        stackTrace: stackTrace,
        category: 'VersionService',
      );
      return null;
    }
  }

  /// Gets the current app version from PackageInfo.
  Future<String> _getCurrentVersion() async {
    final packageInfo = await PackageInfo.fromPlatform();
    return packageInfo.version; // e.g., "1.0.0"
  }

  /// Fetches the latest app version from the backend API.
  ///
  /// Returns the version string or `null` if the request fails.
  Future<String?> _fetchLatestVersion() async {
    try {
      // TODO: Update this endpoint when backend implements app version endpoint
      // For now, using a placeholder endpoint structure
      final response = await _apiClient.get<Map<String, dynamic>>(
        '${ApiConstants.apiPrefix}/app/version',
      );

      if (response.data != null) {
        return response.data!['version'] as String?;
      }
      return null;
    } catch (e) {
      AppLogger.warning(
        'Failed to fetch latest version from backend',
        error: e,
        category: 'VersionService',
      );
      return null;
    }
  }

  /// Compares two semantic version strings.
  ///
  /// Returns:
  /// - Negative number if [current] < [latest]
  /// - Zero if [current] == [latest]
  /// - Positive number if [current] > [latest]
  ///
  /// Supports semantic versioning format: major.minor.patch
  /// Examples: "1.0.0", "2.1.3", "1.0.0-beta"
  int _compareVersions(String current, String latest) {
    final currentParts = _parseVersion(current);
    final latestParts = _parseVersion(latest);

    // Compare major version
    if (currentParts[0] != latestParts[0]) {
      return currentParts[0] - latestParts[0];
    }

    // Compare minor version
    if (currentParts[1] != latestParts[1]) {
      return currentParts[1] - latestParts[1];
    }

    // Compare patch version
    return currentParts[2] - latestParts[2];
  }

  /// Parses a version string into [major, minor, patch] integers.
  ///
  /// Handles versions with pre-release tags (e.g., "1.0.0-beta" -> [1, 0, 0])
  List<int> _parseVersion(String version) {
    // Remove pre-release suffix if present (e.g., "1.0.0-beta" -> "1.0.0")
    final cleanVersion = version.split('-').first;

    final parts = cleanVersion.split('.');

    return [
      int.tryParse(parts.elementAtOrNull(0) ?? '0') ?? 0, // major
      int.tryParse(parts.elementAtOrNull(1) ?? '0') ?? 0, // minor
      int.tryParse(parts.elementAtOrNull(2) ?? '0') ?? 0, // patch
    ];
  }

  /// Determines if an update is mandatory based on version difference.
  ///
  /// Mandatory: Major version difference (e.g., 1.x.x -> 2.x.x)
  /// Optional: Minor or patch version difference
  bool _isMandatoryUpdate(String current, String latest) {
    final currentParts = _parseVersion(current);
    final latestParts = _parseVersion(latest);

    // Major version difference = mandatory update
    return currentParts[0] != latestParts[0];
  }

  /// Checks if enough time has passed since last version check.
  bool _shouldCheckForUpdate() {
    final lastCheckTimestamp = _prefs.getInt(_lastCheckKey);

    if (lastCheckTimestamp == null) {
      return true; // Never checked before
    }

    final lastCheck = DateTime.fromMillisecondsSinceEpoch(lastCheckTimestamp);
    final now = DateTime.now();
    final timeSinceLastCheck = now.difference(lastCheck);

    return timeSinceLastCheck >= _checkInterval;
  }

  /// Updates the last check timestamp to current time.
  Future<void> _updateLastCheckTimestamp() async {
    await _prefs.setInt(_lastCheckKey, DateTime.now().millisecondsSinceEpoch);
  }

  /// Clears the last check timestamp (useful for testing).
  Future<void> clearLastCheckTimestamp() async {
    await _prefs.remove(_lastCheckKey);
  }
}
