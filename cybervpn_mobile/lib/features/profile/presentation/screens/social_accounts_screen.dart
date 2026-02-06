import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';

// ---------------------------------------------------------------------------
// SocialAccountsScreen
// ---------------------------------------------------------------------------

/// Screen for managing linked social OAuth accounts (Telegram, GitHub).
///
/// Displays connection status for each provider and allows the user to
/// link or unlink accounts. Linking initiates an OAuth flow in the system
/// browser. Unlinking requires confirmation and removes the provider association.
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('Social Accounts'),
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
                'Link your social accounts for easier sign-in and account recovery.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: Spacing.lg),

              // Telegram provider
              _ProviderCard(
                key: const Key('provider_telegram'),
                provider: OAuthProvider.telegram,
                isLinked: linkedProviders.contains(OAuthProvider.telegram),
                linkedUsername: _getTelegramUsername(profile?.telegramId),
                onLinkTap: () => _handleLinkProvider(
                  context,
                  OAuthProvider.telegram,
                ),
                onUnlinkTap: () => _showUnlinkDialog(
                  context,
                  OAuthProvider.telegram,
                ),
              ),
              const SizedBox(height: Spacing.md),

              // GitHub provider
              _ProviderCard(
                key: const Key('provider_github'),
                provider: OAuthProvider.github,
                isLinked: linkedProviders.contains(OAuthProvider.github),
                linkedUsername: null, // Backend doesn't expose GitHub username yet
                onLinkTap: () => _handleLinkProvider(
                  context,
                  OAuthProvider.github,
                ),
                onUnlinkTap: () => _showUnlinkDialog(
                  context,
                  OAuthProvider.github,
                ),
              ),
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
            content: Text('Completing $providerDisplayName link...'),
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
          content: Text('Failed to complete OAuth link: $e'),
          backgroundColor: colorScheme.error,
        ),
      );
    }
  }

  /// Extract a displayable Telegram username from the telegramId field.
  /// Returns null if no Telegram ID is available.
  String? _getTelegramUsername(String? telegramId) {
    if (telegramId == null || telegramId.isEmpty) return null;
    return '@$telegramId';
  }

  /// Initiates the OAuth linking flow by launching the authorization URL in browser
  Future<void> _handleLinkProvider(
    BuildContext context,
    OAuthProvider provider,
  ) async {
    try {
      unawaited(HapticFeedback.lightImpact());

      // Get the authorization URL from the backend
      final notifier = ref.read(profileProvider.notifier);
      final String authUrl;
      if (provider == OAuthProvider.telegram) {
        authUrl = await notifier.getTelegramAuthUrl();
      } else if (provider == OAuthProvider.github) {
        authUrl = await notifier.getGithubAuthUrl();
      } else {
        throw UnsupportedError('Provider ${provider.name} not supported');
      }

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
      final messenger = ScaffoldMessenger.of(context);
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'Complete authorization in your browser, then return to the app.',
          ),
          duration: Duration(seconds: 4),
        ),
      );
    } catch (e) {
      AppLogger.error(
        'Failed to initiate OAuth link for ${provider.name}',
        error: e,
        category: 'oauth',
      );
      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      final colorScheme = Theme.of(context).colorScheme;
      final providerDisplayName = _providerName(provider);
      messenger.showSnackBar(
        SnackBar(
          content: Text('Failed to link $providerDisplayName: $e'),
          backgroundColor: colorScheme.error,
        ),
      );
    }
  }

  /// Shows a confirmation dialog before unlinking the provider.
  Future<void> _showUnlinkDialog(
    BuildContext context,
    OAuthProvider provider,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Unlink ${_providerName(provider)}?'),
        content: Text(
          'You will need to re-authorize to link this account again. '
          'This will not delete your ${_providerName(provider)} account.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Unlink'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await _handleUnlinkProvider(context, provider);
    }
  }

  /// Unlinks the provider after user confirmation.
  Future<void> _handleUnlinkProvider(
    BuildContext context,
    OAuthProvider provider,
  ) async {
    try {
      unawaited(HapticFeedback.lightImpact());

      await ref.read(profileProvider.notifier).unlinkAccount(provider);

      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      final providerDisplayName = _providerName(provider);
      messenger.showSnackBar(
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
      final messenger = ScaffoldMessenger.of(context);
      final colorScheme = Theme.of(context).colorScheme;
      final providerDisplayName = _providerName(provider);
      messenger.showSnackBar(
        SnackBar(
          content: Text('Failed to unlink $providerDisplayName: $e'),
          backgroundColor: colorScheme.error,
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
                        isLinked ? 'Linked' : 'Not Linked',
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
                child: const Text('Unlink'),
              )
            else
              FilledButton(
                key: Key('link_${provider.name}'),
                onPressed: onLinkTap,
                child: const Text('Link'),
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
    };
  }

  String _getProviderName() {
    return switch (provider) {
      OAuthProvider.telegram => 'Telegram',
      OAuthProvider.github => 'GitHub',
      OAuthProvider.google => 'Google',
      OAuthProvider.apple => 'Apple',
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
                child: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
