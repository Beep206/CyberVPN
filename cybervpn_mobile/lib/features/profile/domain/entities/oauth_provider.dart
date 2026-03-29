/// Supported OAuth providers for social account linking and OAuth login.
enum OAuthProvider {
  telegram,
  github,
  google,
  facebook,
  apple,
  discord,
  microsoft,
  twitter,
}

/// Providers that stay in code but are hidden from active mobile auth entry points.
const Set<OAuthProvider> kDisabledMobileAuthEntryProviders = {
  OAuthProvider.apple,
};

/// Providers that should not appear as new mobile social-link options.
const Set<OAuthProvider> kDisabledMobileLinkEntryProviders = {
  OAuthProvider.apple,
};

extension OAuthProviderMobileVisibility on OAuthProvider {
  /// Whether this provider should be visible in active mobile auth UI.
  bool get isMobileAuthEntryEnabled =>
      !kDisabledMobileAuthEntryProviders.contains(this);

  /// Whether this provider should be visible as a mobile link entry point.
  bool get isMobileLinkEntryEnabled =>
      !kDisabledMobileLinkEntryProviders.contains(this);
}
