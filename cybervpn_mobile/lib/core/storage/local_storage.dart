import 'package:shared_preferences/shared_preferences.dart';

/// Wrapper for SharedPreferences providing plaintext storage for non-sensitive data.
///
/// **USE THIS FOR**:
/// - App settings and preferences (theme, locale, notifications)
/// - Feature flags and toggles
/// - Public metadata (server lists, favorite IDs)
/// - App state (onboarding complete, last selected items)
/// - UI preferences (MTU, DNS provider selection)
///
/// **⚠️ SECURITY WARNING**:
/// - Data is stored in PLAINTEXT XML files
/// - Readable via device backups
/// - Accessible on rooted/jailbroken devices
/// - NO encryption at rest
///
/// **DO NOT USE** for credentials, tokens, passwords, or any sensitive data!
/// Use [SecureStorageWrapper] instead.
/// See [STORAGE_GUIDELINES.md] for data classification rules.
class LocalStorageWrapper {
  SharedPreferences? _prefs;

  Future<SharedPreferences> get prefs async {
    _prefs ??= await SharedPreferences.getInstance();
    return _prefs!;
  }

  Future<void> setString(String key, String value) async =>
      (await prefs).setString(key, value);

  Future<String?> getString(String key) async =>
      (await prefs).getString(key);

  Future<void> setBool(String key, bool value) async =>
      (await prefs).setBool(key, value);

  Future<bool?> getBool(String key) async => (await prefs).getBool(key);

  Future<void> setInt(String key, int value) async =>
      (await prefs).setInt(key, value);

  Future<int?> getInt(String key) async => (await prefs).getInt(key);

  Future<void> remove(String key) async => (await prefs).remove(key);

  Future<void> clear() async => (await prefs).clear();

  Future<void> setStringList(String key, List<String> value) async =>
      (await prefs).setStringList(key, value);

  Future<List<String>?> getStringList(String key) async =>
      (await prefs).getStringList(key);

  // ── Common Non-Sensitive Storage Keys ─────────────────────────────────────

  // NON-SENSITIVE: UI theme preference - SharedPreferences is sufficient
  static const String themeKey = 'theme_mode';

  // NON-SENSITIVE: Locale preference - SharedPreferences is sufficient
  static const String localeKey = 'locale';

  // NON-SENSITIVE: Onboarding completion flag - SharedPreferences is sufficient
  static const String onboardingCompleteKey = 'onboarding_complete';

  // NON-SENSITIVE: Last selected server ID (just UUID) - SharedPreferences is sufficient
  static const String lastServerKey = 'last_server_id';

  // NON-SENSITIVE: Kill switch feature toggle - SharedPreferences is sufficient
  static const String killSwitchKey = 'kill_switch_enabled';

  // NON-SENSITIVE: Split tunnel app list - SharedPreferences is sufficient
  static const String splitTunnelKey = 'split_tunnel_apps';

  // NON-SENSITIVE: Auto-connect preference - SharedPreferences is sufficient
  static const String autoConnectKey = 'auto_connect';
}
