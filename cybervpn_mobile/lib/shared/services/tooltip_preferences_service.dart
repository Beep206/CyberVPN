import 'package:shared_preferences/shared_preferences.dart';

/// Service to track which feature tooltips have been shown to the user.
///
/// Uses SharedPreferences to persist tooltip visibility state.
/// Each tooltip is identified by a unique string ID.
class TooltipPreferencesService {
  static const String _keyPrefix = 'tooltip_shown_';

  SharedPreferences? _prefs;

  /// Initialize the SharedPreferences instance.
  ///
  /// This should be called before using the service.
  Future<void> initialize() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  /// Check if a tooltip with the given [tooltipId] has been shown before.
  ///
  /// Returns `true` if the tooltip has been shown, `false` otherwise.
  ///
  /// Example:
  /// ```dart
  /// final hasShown = await service.hasShownTooltip('servers_fastest_button');
  /// ```
  Future<bool> hasShownTooltip(String tooltipId) async {
    await initialize();
    return _prefs?.getBool('$_keyPrefix$tooltipId') ?? false;
  }

  /// Mark a tooltip with the given [tooltipId] as shown.
  ///
  /// This persists the state so the tooltip won't be shown again.
  ///
  /// Example:
  /// ```dart
  /// await service.markTooltipAsShown('servers_fastest_button');
  /// ```
  Future<void> markTooltipAsShown(String tooltipId) async {
    await initialize();
    await _prefs?.setBool('$_keyPrefix$tooltipId', true);
  }

  /// Reset all tooltips to unshown state.
  ///
  /// This is useful for testing or debugging purposes.
  /// Use with caution as it will clear all tooltip preferences.
  ///
  /// Example:
  /// ```dart
  /// await service.resetAllTooltips();
  /// ```
  Future<void> resetAllTooltips() async {
    await initialize();
    final keys = _prefs?.getKeys() ?? {};
    for (final key in keys) {
      if (key.startsWith(_keyPrefix)) {
        await _prefs?.remove(key);
      }
    }
  }

  /// Reset a specific tooltip to unshown state.
  ///
  /// This allows re-showing a specific tooltip without affecting others.
  ///
  /// Example:
  /// ```dart
  /// await service.resetTooltip('servers_fastest_button');
  /// ```
  Future<void> resetTooltip(String tooltipId) async {
    await initialize();
    await _prefs?.remove('$_keyPrefix$tooltipId');
  }
}
