import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';

// ---------------------------------------------------------------------------
// Subscription URL Import Screen
// ---------------------------------------------------------------------------

/// Full-screen interface for managing subscription URL imports.
///
/// Provides:
/// - Manual URL input field with paste button
/// - Import button to fetch and parse subscription URLs
/// - List of imported subscription URLs with metadata
/// - Per-URL refresh and delete actions
/// - Pull-to-refresh for all subscriptions
class SubscriptionUrlScreen extends ConsumerStatefulWidget {
  const SubscriptionUrlScreen({super.key});

  @override
  ConsumerState<SubscriptionUrlScreen> createState() =>
      _SubscriptionUrlScreenState();
}

class _SubscriptionUrlScreenState extends ConsumerState<SubscriptionUrlScreen> {
  late final TextEditingController _urlController;
  final _formKey = GlobalKey<FormState>();

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  // ── Clipboard paste ───────────────────────────────────────────────────────

  Future<void> _pasteFromClipboard() async {
    try {
      final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
      final text = clipboardData?.text?.trim();
      if (text != null && text.isNotEmpty) {
        setState(() {
          _urlController.text = text;
        });
      }
    } catch (e) {
      AppLogger.debug('Failed to read clipboard', error: e);
      if (mounted) {
        _showSnackbar(AppLocalizations.of(context).configImportPasteFailed);
      }
    }
  }

  // ── Import subscription URL ───────────────────────────────────────────────

  Future<void> _importSubscriptionUrl() async {
    if (!_formKey.currentState!.validate()) return;

    final url = _urlController.text.trim();
    final notifier = ref.read(configImportProvider.notifier);

    final importedConfigs = await notifier.importFromSubscriptionUrl(url);

    if (!mounted) return;

    final l10n = AppLocalizations.of(context);
    if (importedConfigs.isNotEmpty) {
      _showSnackbar(l10n.configImportServersImported(importedConfigs.length));
      _urlController.clear();
    } else {
      _showSnackbar(l10n.configImportSubscriptionFailed);
    }
  }

  // ── UI feedback ───────────────────────────────────────────────────────────

  void _showSnackbar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final isImporting = ref.watch(isImportingProvider);

    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.configImportSubscriptionUrlTitle),
      ),
      body: Column(
        children: [
          // URL input section
          _UrlInputSection(
            formKey: _formKey,
            urlController: _urlController,
            isImporting: isImporting,
            onPaste: _pasteFromClipboard,
            onImport: _importSubscriptionUrl,
          ),

          const Divider(height: 1),

          // Subscription list section
          Expanded(
            child: _SubscriptionUrlList(),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// URL Input Section
// ---------------------------------------------------------------------------

/// The top section containing the URL text field and import button.
class _UrlInputSection extends StatelessWidget {
  const _UrlInputSection({
    required this.formKey,
    required this.urlController,
    required this.isImporting,
    required this.onPaste,
    required this.onImport,
  });

  final GlobalKey<FormState> formKey;
  final TextEditingController urlController;
  final bool isImporting;
  final VoidCallback onPaste;
  final VoidCallback onImport;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // URL input field
            TextFormField(
              controller: urlController,
              enabled: !isImporting,
              keyboardType: TextInputType.url,
              textInputAction: TextInputAction.done,
              decoration: InputDecoration(
                labelText: l10n.configImportSubscriptionUrlLabel,
                hintText: l10n.configImportSubscriptionUrlHint,
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  key: const Key('paste_button'),
                  icon: const Icon(Icons.content_paste),
                  tooltip: l10n.configImportPasteTooltip,
                  onPressed: isImporting ? null : onPaste,
                ),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return l10n.configImportPleaseEnterUrl;
                }
                final uri = Uri.tryParse(value.trim());
                if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
                  return l10n.configImportPleaseEnterValidUrl;
                }
                return null;
              },
            ),

            const SizedBox(height: 12),

            // Import button
            FilledButton.icon(
              key: const Key('import_button'),
              onPressed: isImporting ? null : onImport,
              icon: isImporting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.download),
              label: Text(isImporting ? l10n.configImportImporting : l10n.configImportImportButton),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Subscription URL List
// ---------------------------------------------------------------------------

/// Displays the list of imported subscription URLs with metadata.
///
/// Shows server count, last updated timestamp, and actions for each URL.
/// Displays an empty state when no subscriptions are imported.
/// Supports pull-to-refresh to update all subscriptions.
class _SubscriptionUrlList extends ConsumerWidget {
  const _SubscriptionUrlList();

  /// Refresh all subscription URLs.
  Future<void> _refreshAllSubscriptions(WidgetRef ref) async {
    // Trigger medium haptic on pull-to-refresh threshold.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    final notifier = ref.read(configImportProvider.notifier);
    try {
      await notifier.refreshSubscriptions();
    } catch (e) {
      AppLogger.error('Failed to refresh subscriptions', error: e);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subscriptions = ref.watch(subscriptionUrlMetadataProvider);

    if (subscriptions.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => _refreshAllSubscriptions(ref),
        child: _EmptyState(),
      );
    }

    return RefreshIndicator(
      key: const Key('refresh_indicator'),
      onRefresh: () => _refreshAllSubscriptions(ref),
      child: ListView.builder(
        key: const Key('subscription_list'),
        padding: const EdgeInsets.all(8),
        itemCount: subscriptions.length,
        itemBuilder: (context, index) {
          final subscription = subscriptions[index];
          return _SubscriptionUrlCard(
            key: Key('subscription_$index'),
            subscription: subscription,
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty State
// ---------------------------------------------------------------------------

/// Shown when no subscription URLs have been imported.
///
/// Uses a scrollable container to support pull-to-refresh gesture.
class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(
              minHeight: constraints.maxHeight,
            ),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.cloud_off_outlined,
                      size: 64,
                      color: theme.colorScheme.onSurfaceVariant
                          .withValues(alpha: 0.5),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      l10n.configImportNoSubscriptionUrls,
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.configImportNoSubscriptionUrlsHint,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant
                            .withValues(alpha: 0.7),
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Subscription URL Card
// ---------------------------------------------------------------------------

/// Card displaying a single subscription URL with metadata and actions.
class _SubscriptionUrlCard extends ConsumerWidget {
  const _SubscriptionUrlCard({
    super.key,
    required this.subscription,
  });

  final SubscriptionUrlMetadata subscription;

  /// Show a confirmation dialog before deleting the subscription.
  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        final dialogL10n = AppLocalizations.of(dialogContext);
        return AlertDialog(
          title: Text(dialogL10n.configImportDeleteSubscriptionTitle),
          content: Text(
            dialogL10n.configImportDeleteSubscriptionContent(subscription.serverCount),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: Text(dialogL10n.commonDelete),
            ),
          ],
        );
      },
    );

    if (confirmed == true && context.mounted) {
      final notifier = ref.read(configImportProvider.notifier);
      await notifier.deleteSubscriptionUrl(subscription.url);

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(l10n.configImportSubscriptionDeleted),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  /// Refresh this specific subscription URL.
  Future<void> _refreshSubscription(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(configImportProvider.notifier);
    await notifier.refreshSubscriptionUrl(subscription.url);

    if (context.mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.configImportSubscriptionRefreshed),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final isImporting = ref.watch(isImportingProvider);

    // Format the last updated timestamp
    final now = DateTime.now();
    final difference = now.difference(subscription.lastUpdated);
    final String timeAgo;

    if (difference.inMinutes < 1) {
      timeAgo = l10n.configImportTimeJustNow;
    } else if (difference.inHours < 1) {
      timeAgo = l10n.configImportTimeMinutesAgo(difference.inMinutes);
    } else if (difference.inDays < 1) {
      timeAgo = l10n.configImportTimeHoursAgo(difference.inHours);
    } else if (difference.inDays < 7) {
      timeAgo = l10n.configImportTimeDaysAgo(difference.inDays);
    } else {
      timeAgo = DateFormat.yMMMd().format(subscription.lastUpdated);
    }

    // Truncate URL for display
    final displayUrl = subscription.url.length > 50
        ? '${subscription.url.substring(0, 47)}...'
        : subscription.url;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 8,
        ),
        title: Text(
          displayUrl,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            '${l10n.configImportServerCount(subscription.serverCount)} \u2022 ${l10n.configImportLastUpdated(timeAgo)}',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Refresh button
            IconButton(
              key: Key('refresh_${subscription.url}'),
              icon: const Icon(Icons.refresh),
              tooltip: l10n.configImportRefreshTooltip,
              onPressed: isImporting
                  ? null
                  : () => _refreshSubscription(context, ref),
            ),

            // Delete button
            IconButton(
              key: Key('delete_${subscription.url}'),
              icon: const Icon(Icons.delete_outline),
              tooltip: l10n.configImportDeleteTooltip,
              onPressed: isImporting
                  ? null
                  : () => _confirmDelete(context, ref),
            ),
          ],
        ),
      ),
    );
  }
}
