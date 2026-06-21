# CyberVPN Flutter Mobile Rules

Apply the root completion contract plus these mobile rules.

- Preserve the existing state-management, navigation, generated-model and
  platform-channel architecture; inspect current conventions before adding an
  abstraction.
- VPN connect/disconnect, permission, foreground/background and recovery paths
  are state machines. Make transitions explicit and test invalid/repeated
  transitions.
- Never log or persist raw subscription links, VPN configs, access tokens,
  private keys or device credentials outside approved secure storage.
- Handle Android/iOS permission denial, process death, network loss, revoked
  credentials and stale server state honestly in the UI.
- Generated Dart files must be regenerated, not edited manually.
- Add unit/widget tests and integration/platform tests for changed VPN,
  lifecycle, auth, deep-link or secure-storage behavior.
- Before VERIFIED run generation, formatting, analyze with fatal warnings,
  full tests and affected platform builds/smokes.
