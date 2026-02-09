import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';

// ---------------------------------------------------------------------------
// SocialAccountsScreen
// ---------------------------------------------------------------------------

/// Screen for managing linked social OAuth accounts.
///
/// Displays connection status for all supported OAuth providers
/// (Telegram, GitHub, Google, Apple, Discord, Microsoft, X) and allows the
/// user to link or unlink accounts. Linking initiates an OAuth flow in the
/// system browser. Unlinking requires confirmation and removes the provider
/// association.
class SocialAccountsScreen extends ConsumerStatefulWidget {
  const SocialAccountsScreen({super.key});

  @override
  ConsumerState<SocialAccountsScreen> createState() =>
      _SocialAccountsScreenState();
}

class _SocialAccountsScreenState extends ConsumerState<SocialAccountsScreen> {
  @override
  void initState() {
    super.initState();
    // Check for OAuth callback parameters on screen load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_handleOAuthCallback());
    });
  }

  @override
  Widget build(BuildContext context) {
    final asyncProfile = ref.watch(profileProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.profileSocialAccounts),
      ),
      body: asyncProfile.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorBody(
          message: error.toString(),
          onRetry: () => ref.invalidate(profileProvider),
        ),
        data: (profileState) {
          final linkedProviders = profileState.linkedProviders;
          final profile = profileState.profile;

          return ListView(
            padding: const EdgeInsets.all(Spacing.md),
            children: [
              // Header description
              Text(
                l10n.profileSocialAccountsDescription,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: Spacing.lg),

              // Provider cards for all supported OAuth providers
              ...OAuthProvider.values.map((provider) => Padding(
                padding: const EdgeInsets.only(bottom: Spacing.md),
                child: _ProviderCard(
                  key: Key('provider_${provider.name}'),
                  provider: provider,
                  isLinked: linkedProviders.contains(provider),
                  linkedUsername: _getLinkedUsername(profile, provider),
                  onLinkTap: () => _handleLinkProvider(
                    context,
                    provider,
                  ),
                  onUnlinkTap: () => _showUnlinkDialog(
                    context,
                    provider,
                  ),
                ),
              )),
            ],
          );
        },
      ),
    );
  }

  /// Handles OAuth callback parameters from deep link navigation
  Future<void> _handleOAuthCallback() async {
    // Check if this navigation contains OAuth callback params
    final uri = ModalRoute.of(context)?.settings.name;
    if (uri == null) return;

    try {
      final parsedUri = Uri.parse(uri);
      final provider = parsedUri.queryParameters['oauth_provider'];
      final code = parsedUri.queryParameters['oauth_code'];

      if (provider != null && code != null) {
        AppLogger.info(
          'Handling OAuth callback: provider=$provider',
          category: 'oauth',
        );

        final oauthProvider = OAuthProvider.values.byName(provider);
        final providerDisplayName = _providerName(oauthProvider);

        if (!mounted) return;
        final messenger = ScaffoldMessenger.of(context);

        messenger.showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).profileSocialCompletingLink(providerDisplayName)),
          ),
        );

        await ref
            .read(profileProvider.notifier)
            .completeOAuthLink(oauthProvider, code);

        if (!mounted) return;
        messenger.showSnackBar(
          SnackBar(
            content: Text('$providerDisplayName account linked successfully'),
            backgroundColor: CyberColors.matrixGreen,
          ),
        );
      }
    } catch (e) {
      AppLogger.error('OAuth callback error', error: e, category: 'oauth');
      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      final colorScheme = Theme.of(context).colorScheme;
      messenger.showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).profileSocialOAuthFailed(e.toString())),
          backgroundColor: colorScheme.error,
        ),
      );
    }
  }

  /// Extract a displayable username for a given provider from the profile.
  ///
  /// Currently only Telegram exposes a user-facing identifier via the
  /// profile entity. Other providers return null until the backend surfaces
  /// additional provider usernames.
  String? _getLinkedUsername(Profile? profile, OAuthProvider provider) {
    if (profile == null) return null;
    return switch (provider) {
      OAuthProvider.telegram => profile.telegramId != null &&
              profile.telegramId!.isNotEmpty
          ? '@${profile.telegramId}'
          : null,
      _ => null, // Backend doesn't expose other provider usernames yet
    };
  }

  /// Initiates the OAuth linking flow by launching the authorization URL in browser.
  ///
  /// For all providers, the generic [ProfileNotifier.getAuthUrl] method is used
  /// which delegates to the backend to obtain the provider-specific authorization URL.
  Future<void> _handleLinkProvider(
    BuildContext ctx,
    OAuthProvider provider,
  ) async {
    try {
      unawaited(HapticFeedback.lightImpact());

      // Get the authorization URL from the backend
      final notifier = ref.read(profileProvider.notifier);
      final authUrl = await notifier.getAuthUrl(provider);

      AppLogger.info(
        'Launching OAuth URL for ${provider.name}',
        category: 'oauth',
      );

      // Launch the URL in the system browser
      final uri = Uri.parse(authUrl);
      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );

      if (!launched) {
        throw Exception('Could not launch OAuth URL');
      }

      if (!mounted) return;
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.profileSocialCompleteAuth),
          duration: const Duration(seconds: 4),
        ),
      );
    } catch (e) {
      AppLogger.error(
        'Failed to initiate OAuth link for ${provider.name}',
        error: e,
        category: 'oauth',
      );
      if (!mounted) return;
      final providerDisplayName = _providerName(provider);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).profileSocialLinkFailed(providerDisplayName, e.toString())),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    }
  }

  /// Shows a confirmation dialog before unlinking the provider.
  Future<void> _showUnlinkDialog(
    BuildContext ctx,
    OAuthProvider provider,
  ) async {
    final providerDisplayName = _providerName(provider);
    final confirmed = await showDialog<bool>(
      context: ctx,
      builder: (dialogCtx) {
        final dialogL10n = AppLocalizations.of(dialogCtx);
        return AlertDialog(
          title: Text(dialogL10n.profileSocialUnlinkConfirm(providerDisplayName)),
          content: Text(
            dialogL10n.profileSocialUnlinkDescription(providerDisplayName),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(false),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogCtx).pop(true),
              child: Text(dialogL10n.profileOauthUnlink),
            ),
          ],
        );
      },
    );

    if (confirmed == true && mounted) {
      await _handleUnlinkProvider(provider);
    }
  }

  /// Unlinks the provider after user confirmation.
  Future<void> _handleUnlinkProvider(OAuthProvider provider) async {
    try {
      unawaited(HapticFeedback.lightImpact());

      await ref.read(profileProvider.notifier).unlinkAccount(provider);

      if (!mounted) return;
      final providerDisplayName = _providerName(provider);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$providerDisplayName account unlinked'),
        ),
      );
    } catch (e) {
      AppLogger.error(
        'Failed to unlink ${provider.name}',
        error: e,
        category: 'oauth',
      );
      if (!mounted) return;
      final providerDisplayName = _providerName(provider);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).profileSocialUnlinkFailed(providerDisplayName, e.toString())),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    }
  }

  String _providerName(OAuthProvider provider) {
    return switch (provider) {
      OAuthProvider.telegram => 'Telegram',
      OAuthProvider.github => 'GitHub',
      OAuthProvider.google => 'Google',
      OAuthProvider.apple => 'Apple',
      OAuthProvider.discord => 'Discord',
      OAuthProvider.microsoft => 'Microsoft',
      OAuthProvider.twitter => 'X',
    };
  }
}

// ---------------------------------------------------------------------------
// Provider Card
// ---------------------------------------------------------------------------

class _ProviderCard extends StatelessWidget {
  const _ProviderCard({
    super.key,
    required this.provider,
    required this.isLinked,
    required this.onLinkTap,
    required this.onUnlinkTap,
    this.linkedUsername,
  });

  final OAuthProvider provider;
  final bool isLinked;
  final String? linkedUsername;
  final VoidCallback onLinkTap;
  final VoidCallback onUnlinkTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Row(
          children: [
            // Provider icon
            Container(
              padding: const EdgeInsets.all(Spacing.sm),
              decoration: BoxDecoration(
                color: colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(Radii.sm),
              ),
              child: Icon(
                _getProviderIcon(),
                size: 28,
                color: colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(width: Spacing.md),

            // Provider name and status
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _getProviderName(),
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: Spacing.xs),
                  Row(
                    children: [
                      // Status indicator
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: isLinked
                              ? CyberColors.matrixGreen
                              : colorScheme.onSurfaceVariant,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: Spacing.xs),
                      // Status text
                      Text(
                        isLinked ? l10n.profileSocialLinked : l10n.profileSocialNotLinked,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                  // Show username if linked
                  if (isLinked && linkedUsername != null) ...[
                    const SizedBox(height: Spacing.xs),
                    Text(
                      linkedUsername!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colorScheme.primary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Action button
            if (isLinked)
              OutlinedButton(
                key: Key('unlink_${provider.name}'),
                onPressed: onUnlinkTap,
                style: OutlinedButton.styleFrom(
                  foregroundColor: colorScheme.error,
                  side: BorderSide(color: colorScheme.error),
                ),
                child: Text(l10n.profileOauthUnlink),
              )
            else
              FilledButton(
                key: Key('link_${provider.name}'),
                onPressed: onLinkTap,
                child: Text(l10n.profileSocialLink),
              ),
          ],
        ),
      ),
    );
  }

  IconData _getProviderIcon() {
    return switch (provider) {
      OAuthProvider.telegram => Icons.telegram,
      OAuthProvider.github => Icons.code,
      OAuthProvider.google => Icons.g_mobiledata,
      OAuthProvider.apple => Icons.apple,
      OAuthProvider.discord => Icons.discord,
      OAuthProvider.microsoft => Icons.window,
      OAuthProvider.twitter => Icons.close, // X icon
    };
  }

  String _getProviderName() {
    return switch (provider) {
      OAuthProvider.telegram => 'Telegram',
      OAuthProvider.github => 'GitHub',
      OAuthProvider.google => 'Google',
      OAuthProvider.apple => 'Apple',
      OAuthProvider.discord => 'Discord',
      OAuthProvider.microsoft => 'Microsoft',
      OAuthProvider.twitter => 'X',
    };
  }
}

// ---------------------------------------------------------------------------
// Error Body
// ---------------------------------------------------------------------------

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: Spacing.md),
            Text(
              message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: Spacing.md),
              FilledButton.tonal(
                onPressed: onRetry,
                child: Text(l10n.retry),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
