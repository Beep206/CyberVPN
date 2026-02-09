/// Certificate pinning configuration for CyberVPN API servers.
///
/// These fingerprints are SHA-256 hashes of the DER-encoded server
/// certificates. They are used by [CertificatePinner] to validate
/// TLS connections and prevent MITM attacks.
///
/// ## How to extract fingerprints
///
/// ```bash
/// # For a live server:
/// echo | openssl s_client -connect api.cybervpn.com:443 2>/dev/null \
///   | openssl x509 -fingerprint -sha256 -noout \
///   | sed 's/sha256 Fingerprint=//'
///
/// # From a certificate file:
/// openssl x509 -in cert.pem -fingerprint -sha256 -noout
/// ```
///
/// ## Rotation
///
/// Always include at least one backup fingerprint so certificate rotation
/// does not require an immediate app update. When rotating:
/// 1. Add the new certificate fingerprint as a backup BEFORE rotation
/// 2. Ship the app update
/// 3. Rotate the server certificate
/// 4. Remove the old fingerprint in the next release
///
/// ## Build configuration
///
/// Fingerprints can be overridden at build time via `--dart-define`:
/// ```bash
/// flutter build apk --dart-define=CERT_FINGERPRINTS=AA:BB:CC:...,DD:EE:FF:...
/// ```
///
/// If `CERT_FINGERPRINTS` is set via dart-define, it takes priority over
/// the constants below.
class CertPins {
  const CertPins._();

  /// SHA-256 fingerprint of the current production API certificate.
  ///
  /// Extract with:
  /// ```bash
  /// echo | openssl s_client -connect api.cybervpn.com:443 2>/dev/null \
  ///   | openssl x509 -fingerprint -sha256 -noout
  /// ```
  static const String production =
      ''; // TODO: Set from `openssl` output before production release

  /// SHA-256 fingerprint of the backup/next production certificate.
  ///
  /// Used during certificate rotation to prevent service disruption.
  static const String productionBackup =
      ''; // TODO: Set backup cert fingerprint

  /// SHA-256 fingerprint of the staging API certificate.
  static const String staging =
      ''; // TODO: Set staging cert fingerprint

  /// All active fingerprints as a list.
  ///
  /// Used by [EnvironmentConfig.certificateFingerprints] when no
  /// `--dart-define` override is provided.
  static List<String> get all => [
        if (production.isNotEmpty) production,
        if (productionBackup.isNotEmpty) productionBackup,
        if (staging.isNotEmpty) staging,
      ];
}
