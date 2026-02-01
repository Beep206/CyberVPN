/// Country flag asset paths for VPN server display.
///
/// Maps ISO 3166-1 alpha-2 country codes to SVG flag asset paths.
/// Flags sourced from circle-flags (MIT license):
/// https://github.com/HatScripts/circle-flags
class FlagAssets {
  const FlagAssets._();

  // ── Base Path ─────────────────────────────────────────────────────────

  static const String _basePath = 'assets/images/flags';

  // ── Fallback Flag ─────────────────────────────────────────────────────

  /// Fallback icon path for unknown or missing country codes.
  /// Returns null to indicate no flag available (caller can show placeholder).
  static const String? fallbackFlag = null;

  // ── Country Code to Flag Asset Map ───────────────────────────────────

  /// Map of uppercase ISO 3166-1 alpha-2 country codes to flag asset paths.
  static const Map<String, String> _flagMap = {
    'US': '$_basePath/us.svg', // United States
    'DE': '$_basePath/de.svg', // Germany
    'JP': '$_basePath/jp.svg', // Japan
    'NL': '$_basePath/nl.svg', // Netherlands
    'SG': '$_basePath/sg.svg', // Singapore
    'GB': '$_basePath/gb.svg', // United Kingdom
    'CA': '$_basePath/ca.svg', // Canada
    'AU': '$_basePath/au.svg', // Australia
    'BR': '$_basePath/br.svg', // Brazil
    'KR': '$_basePath/kr.svg', // South Korea
    'IN': '$_basePath/in.svg', // India
    'FR': '$_basePath/fr.svg', // France
    'CH': '$_basePath/ch.svg', // Switzerland
    'SE': '$_basePath/se.svg', // Sweden
    'FI': '$_basePath/fi.svg', // Finland
    'PL': '$_basePath/pl.svg', // Poland
    'RU': '$_basePath/ru.svg', // Russia
    'UA': '$_basePath/ua.svg', // Ukraine
    'HK': '$_basePath/hk.svg', // Hong Kong
  };

  // ── Public API ────────────────────────────────────────────────────────

  /// Get the flag asset path for a given country code.
  ///
  /// [countryCode] should be an ISO 3166-1 alpha-2 code (case-insensitive).
  /// Returns the asset path if found, or [fallbackFlag] (null) if not found.
  ///
  /// Example:
  /// ```dart
  /// final usFlag = FlagAssets.getFlag('US'); // 'assets/images/flags/us.svg'
  /// final unknownFlag = FlagAssets.getFlag('XX'); // null
  /// ```
  static String? getFlag(String countryCode) {
    final code = countryCode.toUpperCase();
    return _flagMap[code] ?? fallbackFlag;
  }

  /// Check if a flag exists for the given country code.
  ///
  /// Example:
  /// ```dart
  /// if (FlagAssets.hasFlag('US')) {
  ///   // Display flag
  /// }
  /// ```
  static bool hasFlag(String countryCode) {
    final code = countryCode.toUpperCase();
    return _flagMap.containsKey(code);
  }

  /// Get all available country codes that have flags.
  ///
  /// Returns a list of uppercase ISO 3166-1 alpha-2 codes.
  static List<String> get availableCodes => _flagMap.keys.toList();

  /// Get the total number of available flags.
  static int get count => _flagMap.length;
}
