import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';

/// Repository interface for managing application settings
///
/// Follows the repository pattern from Clean Architecture.
/// The concrete implementation in the data layer handles
/// persistence (SharedPreferences, etc.).
abstract class SettingsRepository {
  /// Get current application settings
  ///
  /// Returns the persisted settings or defaults if none are saved
  Future<AppSettings> getSettings();

  /// Update application settings
  ///
  /// Persists the provided settings, replacing the current values
  Future<void> updateSettings(AppSettings settings);

  /// Reset settings to default values
  ///
  /// Clears all persisted settings so defaults are used on next read
  Future<void> resetSettings();
}
