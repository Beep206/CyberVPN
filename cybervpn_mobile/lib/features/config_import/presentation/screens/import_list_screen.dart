import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';

// ---------------------------------------------------------------------------
// Import List Screen
// ---------------------------------------------------------------------------

/// Screen listing all imported custom VPN configurations with management
/// actions, grouped by import source.
///
/// Features:
/// - Configs grouped by source (QR Code, Clipboard, Subscription, etc.)
/// - Per-item actions: connect, edit name, delete, test connection, export QR
/// - Pull-to-refresh for subscription configs
/// - FAB with import options (QR / Clipboard / URL)
/// - Clear All via AppBar overflow menu
/// - Empty state illustration
class ImportListScreen extends ConsumerStatefulWidget {
  const ImportListScreen({super.key});

  @override
  ConsumerState<ImportListScreen> createState() => _ImportListScreenState();
}

class _ImportListScreenState extends ConsumerState<ImportListScreen> {
  /// Set of config IDs currently being tested for connection.
  final Set<String> _testingIds = {};

  @override
  void initState() {
    super.initState();
    // Auto-check clipboard for VPN configs when screen opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_checkClipboardOnOpen());
    });
  }

  /// Check clipboard for VPN config links when screen opens.
  Future<void> _checkClipboardOnOpen() async {
    final notifier = ref.read(configImportProvider.notifier);
    final clipboardUri = await notifier.checkClipboard();
    if (clipboardUri != null && mounted) {
      final l10n = AppLocalizations.of(context);
      _showSnackbar(l10n.configImportVpnConfigDetected);
    }
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  Future<void> _onRefresh() async {
    await ref.read(configImportProvider.notifier).refreshSubscriptions();
  }

  void _onDeleteConfig(ImportedConfig config) {
    final l10n = AppLocalizations.of(context);
    unawaited(showDialog<void>(
      context: context,
      builder: (ctx) {
        final dialogL10n = AppLocalizations.of(ctx);
        return AlertDialog(
          title: Text(dialogL10n.configImportDeleteServerTitle),
          content: Text(dialogL10n.configImportRemoveServerContent(config.name)),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(ctx).pop();
                unawaited(ref.read(configImportProvider.notifier).deleteConfig(config.id));
                _showSnackbar(l10n.configImportServerRemoved);
              },
              child: Text(dialogL10n.commonDelete),
            ),
          ],
        );
      },
    ));
  }

  void _onEditName(ImportedConfig config) {
    final controller = TextEditingController(text: config.name);
    final l10n = AppLocalizations.of(context);

    unawaited(showDialog<void>(
      context: context,
      builder: (ctx) {
        final dialogL10n = AppLocalizations.of(ctx);
        return AlertDialog(
          title: Text(dialogL10n.configImportRenameServerTitle),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: InputDecoration(
              labelText: dialogL10n.configImportServerNameLabel,
              border: const OutlineInputBorder(),
            ),
            onSubmitted: (value) {
              final name = value.trim();
              if (name.isNotEmpty) {
                Navigator.of(ctx).pop();
                unawaited(ref
                    .read(configImportProvider.notifier)
                    .updateConfigName(config.id, name));
                _showSnackbar(l10n.configImportServerRenamed);
              }
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () {
                final name = controller.text.trim();
                if (name.isNotEmpty) {
                  Navigator.of(ctx).pop();
                  unawaited(ref
                      .read(configImportProvider.notifier)
                      .updateConfigName(config.id, name));
                  _showSnackbar(l10n.configImportServerRenamed);
                }
              },
              child: Text(dialogL10n.commonSave),
            ),
          ],
        );
      },
    ).whenComplete(controller.dispose));
  }

  Future<void> _onTestConnection(ImportedConfig config) async {
    if (_testingIds.contains(config.id)) return;

    setState(() => _testingIds.add(config.id));
    final reachable =
        await ref.read(configImportProvider.notifier).testConnection(config.id);
    if (mounted) {
      setState(() => _testingIds.remove(config.id));
      final l10n = AppLocalizations.of(context);
      _showSnackbar(
        reachable ? l10n.configImportServerReachable : l10n.configImportServerUnreachable,
      );
    }
  }

  void _onExportQr(ImportedConfig config) {
    unawaited(showDialog<void>(
      context: context,
      builder: (ctx) {
        final theme = Theme.of(ctx);
        final dialogL10n = AppLocalizations.of(ctx);
        return AlertDialog(
          title: Text(dialogL10n.configImportExportQrTitle),
          content: SizedBox(
            width: 260,
            height: 300,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                QrImageView(
                  key: const Key('export_qr_image'),
                  data: config.rawUri,
                  version: QrVersions.auto,
                  size: 220,
                  backgroundColor: Colors.white,
                ),
                const SizedBox(height: 12),
                Text(
                  config.name,
                  style: theme.textTheme.bodyMedium,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(dialogL10n.commonClose),
            ),
          ],
        );
      },
    ));
  }

  void _onClearAll() {
    final l10n = AppLocalizations.of(context);
    unawaited(showDialog<void>(
      context: context,
      builder: (ctx) {
        final dialogL10n = AppLocalizations.of(ctx);
        return AlertDialog(
          title: Text(dialogL10n.configImportClearAllTitle),
          content: Text(
            dialogL10n.configImportClearAllContent,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: Theme.of(ctx).colorScheme.error,
              ),
              onPressed: () {
                Navigator.of(ctx).pop();
                unawaited(ref.read(configImportProvider.notifier).deleteAll());
                _showSnackbar(l10n.configImportAllServersRemoved);
              },
              child: Text(dialogL10n.configImportClearAllButton),
            ),
          ],
        );
      },
    ));
  }

  void _onFabPressed() {
    final l10n = AppLocalizations.of(context);
    unawaited(showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        final sheetL10n = AppLocalizations.of(ctx);
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Handle bar
              Padding(
                padding: const EdgeInsets.only(top: 12, bottom: 8),
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Theme.of(ctx)
                        .colorScheme
                        .outline
                        .withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              ListTile(
                leading: const Icon(Icons.content_paste),
                title: Text(sheetL10n.configImportFromClipboard),
                onTap: () async {
                  Navigator.of(ctx).pop();
                  final notifier = ref.read(configImportProvider.notifier);
                  final clipboardUri = await notifier.checkClipboard();
                  if (clipboardUri != null && mounted) {
                    final imported = await notifier.importFromUri(
                      clipboardUri,
                      source: ImportSource.clipboard,
                    );
                    if (mounted) {
                      _showSnackbar(
                        imported != null
                            ? l10n.configImportServerAdded(imported.name)
                            : l10n.configImportNoValidConfig,
                      );
                    }
                  } else if (mounted) {
                    _showSnackbar(l10n.configImportNoConfigInClipboard);
                  }
                },
              ),
              ListTile(
                leading: const Icon(Icons.qr_code_scanner),
                title: Text(sheetL10n.configImportScanQrButton),
                onTap: () {
                  Navigator.of(ctx).pop();
                  unawaited(Navigator.of(context).pushNamed('/qr-scanner'));
                },
              ),
              ListTile(
                leading: const Icon(Icons.link),
                title: Text(sheetL10n.configImportFromSubscriptionUrl),
                onTap: () {
                  Navigator.of(ctx).pop();
                  _showSubscriptionUrlDialog();
                },
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    ));
  }

  void _showSubscriptionUrlDialog() {
    final controller = TextEditingController();
    final l10n = AppLocalizations.of(context);

    unawaited(showDialog<void>(
      context: context,
      builder: (ctx) {
        final dialogL10n = AppLocalizations.of(ctx);
        return AlertDialog(
          title: Text(dialogL10n.configImportSubscriptionUrlLabel),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: InputDecoration(
              labelText: dialogL10n.configImportSubscriptionUrlHint,
              hintText: 'https://...',
              border: const OutlineInputBorder(),
            ),
            keyboardType: TextInputType.url,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () async {
                final url = controller.text.trim();
                if (url.isEmpty) return;
                Navigator.of(ctx).pop();
                final notifier = ref.read(configImportProvider.notifier);
                final configs = await notifier.importFromSubscriptionUrl(url);
                if (mounted) {
                  _showSnackbar(
                    configs.isNotEmpty
                        ? l10n.configImportServersImported(configs.length)
                        : l10n.configImportNoServersAtUrl,
                  );
                }
              },
              child: Text(dialogL10n.configImportImportButton),
            ),
          ],
        );
      },
    ).whenComplete(controller.dispose));
  }

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

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /// Group configs by their [ImportSource].
  Map<ImportSource, List<ImportedConfig>> _groupBySource(
    List<ImportedConfig> configs,
  ) {
    final grouped = <ImportSource, List<ImportedConfig>>{};
    for (final config in configs) {
      grouped.putIfAbsent(config.source, () => []).add(config);
    }
    return grouped;
  }

  String _sourceLabel(ImportSource source, AppLocalizations l10n) {
    return switch (source) {
      ImportSource.qrCode => l10n.configImportSourceQrCode,
      ImportSource.clipboard => l10n.configImportSourceClipboard,
      ImportSource.subscriptionUrl => l10n.configImportSourceSubscription,
      ImportSource.deepLink => l10n.configImportSourceDeepLink,
      ImportSource.manual => l10n.configImportSourceManual,
    };
  }

  IconData _sourceIcon(ImportSource source) {
    return switch (source) {
      ImportSource.qrCode => Icons.qr_code,
      ImportSource.clipboard => Icons.content_paste,
      ImportSource.subscriptionUrl => Icons.cloud_download_outlined,
      ImportSource.deepLink => Icons.link,
      ImportSource.manual => Icons.edit_note,
    };
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(configImportProvider);
    final isImporting = ref.watch(isImportingProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.configImportCustomServersTitle),
        actions: [
          PopupMenuButton<String>(
            key: const Key('custom_servers_menu'),
            onSelected: (value) {
              if (value == 'clear_all') _onClearAll();
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'clear_all',
                child: Row(
                  children: [
                    const Icon(Icons.delete_sweep, size: 20),
                    const SizedBox(width: 12),
                    Text(l10n.configImportClearAllButton),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: asyncState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(
          error: error.toString(),
          onRetry: () => ref.invalidate(configImportProvider),
        ),
        data: (state) {
          if (state.customServers.isEmpty) {
            return _EmptyStateView(onImport: _onFabPressed);
          }
          return _buildServerList(context, state, isImporting);
        },
      ),
      floatingActionButton: FloatingActionButton(
        key: const Key('import_fab'),
        onPressed: _onFabPressed,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildServerList(
    BuildContext context,
    ConfigImportState state,
    bool isImporting,
  ) {
    final grouped = _groupBySource(state.customServers);
    final l10n = AppLocalizations.of(context);

    // Define a stable source order
    const sourceOrder = [
      ImportSource.qrCode,
      ImportSource.clipboard,
      ImportSource.subscriptionUrl,
      ImportSource.deepLink,
      ImportSource.manual,
    ];

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: CustomScrollView(
        slivers: [
          // Loading indicator for import operations
          if (isImporting)
            const SliverToBoxAdapter(
              child: LinearProgressIndicator(),
            ),

          // Grouped server sections
          for (final source in sourceOrder)
            if (grouped.containsKey(source)) ...[
              // Section header
              SliverToBoxAdapter(
                child: _SourceGroupHeader(
                  label: _sourceLabel(source, l10n),
                  icon: _sourceIcon(source),
                  count: grouped[source]!.length,
                ),
              ),
              // Server items
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final config = grouped[source]![index];
                    return _CustomServerTile(
                      key: Key('server_tile_${config.id}'),
                      config: config,
                      isTesting: _testingIds.contains(config.id),
                      onDelete: () => _onDeleteConfig(config),
                      onEditName: () => _onEditName(config),
                      onTestConnection: () => _onTestConnection(config),
                      onExportQr: () => _onExportQr(config),
                    );
                  },
                  childCount: grouped[source]!.length,
                ),
              ),
            ],

          // Bottom padding for FAB
          const SliverPadding(padding: EdgeInsets.only(bottom: 80)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Source Group Header
// ---------------------------------------------------------------------------

class _SourceGroupHeader extends StatelessWidget {
  const _SourceGroupHeader({
    required this.label,
    required this.icon,
    required this.count,
  });

  final String label;
  final IconData icon;
  final int count;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Row(
        children: [
          Icon(icon, size: 18, color: colorScheme.primary),
          const SizedBox(width: 8),
          Text(
            label,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$count',
              style: theme.textTheme.labelSmall?.copyWith(
                color: colorScheme.onPrimaryContainer,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Custom Server Tile
// ---------------------------------------------------------------------------

class _CustomServerTile extends StatelessWidget {
  const _CustomServerTile({
    super.key,
    required this.config,
    required this.isTesting,
    required this.onDelete,
    required this.onEditName,
    required this.onTestConnection,
    required this.onExportQr,
  });

  final ImportedConfig config;
  final bool isTesting;
  final VoidCallback onDelete;
  final VoidCallback onEditName;
  final VoidCallback onTestConnection;
  final VoidCallback onExportQr;

  Color? _reachabilityColor(bool? isReachable, ColorScheme colorScheme) {
    if (isReachable == null) return null;
    return isReachable ? colorScheme.tertiary : colorScheme.error;
  }

  String _reachabilityLabel(bool? isReachable, AppLocalizations l10n) {
    if (isReachable == null) return l10n.configImportNotTested;
    return isReachable ? l10n.configImportReachable : l10n.configImportUnreachable;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            // Leading: protocol icon
            Icon(
              Icons.vpn_key_outlined,
              color: colorScheme.primary,
              size: 28,
            ),
            const SizedBox(width: 12),

            // Title + subtitle
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Server name
                  Text(
                    config.name,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: colorScheme.onSurface,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),

                  // Address + protocol badge
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          '${config.serverAddress}:${config.port}',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      _ProtocolBadge(protocol: config.protocol),
                    ],
                  ),
                  const SizedBox(height: 4),

                  // Reachability status
                  Row(
                    children: [
                      if (isTesting)
                        const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      else
                        Icon(
                          config.isReachable == true
                              ? Icons.check_circle
                              : config.isReachable == false
                                  ? Icons.cancel
                                  : Icons.help_outline,
                          size: 14,
                          color: _reachabilityColor(config.isReachable, colorScheme) ??
                              colorScheme.onSurfaceVariant,
                        ),
                      const SizedBox(width: 4),
                      Text(
                        isTesting
                            ? l10n.configImportTesting
                            : _reachabilityLabel(config.isReachable, l10n),
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: _reachabilityColor(config.isReachable, colorScheme) ??
                              colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Action menu
            PopupMenuButton<String>(
              key: Key('server_menu_${config.id}'),
              onSelected: (value) {
                switch (value) {
                  case 'test':
                    onTestConnection();
                  case 'edit':
                    onEditName();
                  case 'export_qr':
                    onExportQr();
                  case 'delete':
                    onDelete();
                }
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'test',
                  child: Row(
                    children: [
                      const Icon(Icons.speed, size: 20),
                      const SizedBox(width: 12),
                      Text(l10n.configImportTestConnection),
                    ],
                  ),
                ),
                PopupMenuItem(
                  value: 'edit',
                  child: Row(
                    children: [
                      const Icon(Icons.edit, size: 20),
                      const SizedBox(width: 12),
                      Text(l10n.configImportEditName),
                    ],
                  ),
                ),
                PopupMenuItem(
                  value: 'export_qr',
                  child: Row(
                    children: [
                      const Icon(Icons.qr_code, size: 20),
                      const SizedBox(width: 12),
                      Text(l10n.configImportExportQrTitle),
                    ],
                  ),
                ),
                PopupMenuItem(
                  value: 'delete',
                  child: Row(
                    children: [
                      Icon(Icons.delete_outline, size: 20, color: colorScheme.error),
                      const SizedBox(width: 12),
                      Text(l10n.commonDelete, style: TextStyle(color: colorScheme.error)),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Protocol Badge
// ---------------------------------------------------------------------------

class _ProtocolBadge extends StatelessWidget {
  const _ProtocolBadge({required this.protocol});

  final String protocol;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: colorScheme.tertiaryContainer,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        protocol.toUpperCase(),
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: colorScheme.onTertiaryContainer,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty State View
// ---------------------------------------------------------------------------

class _EmptyStateView extends ConsumerStatefulWidget {
  const _EmptyStateView({required this.onImport});

  final VoidCallback onImport;

  @override
  ConsumerState<_EmptyStateView> createState() => _EmptyStateViewState();
}

class _EmptyStateViewState extends ConsumerState<_EmptyStateView> {
  final _uriController = TextEditingController();
  bool _isImporting = false;

  @override
  void dispose() {
    _uriController.dispose();
    super.dispose();
  }

  Future<void> _pasteAndImport() async {
    final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
    final text = clipboardData?.text?.trim();
    if (text != null && text.isNotEmpty) {
      _uriController.text = text;
      unawaited(_importUri(text));
    }
  }

  Future<void> _importUri(String uri) async {
    if (uri.isEmpty) return;
    setState(() => _isImporting = true);
    final notifier = ref.read(configImportProvider.notifier);
    final imported = await notifier.importFromUri(uri, source: ImportSource.clipboard);
    if (mounted) {
      setState(() => _isImporting = false);
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            imported != null
                ? l10n.configImportServerAdded(imported.name)
                : l10n.configImportNoValidConfig,
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
      if (imported != null) _uriController.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.dns_outlined,
              size: 80,
              color: colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: 24),
            Text(
              l10n.configImportNoCustomServers,
              style: theme.textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              l10n.configImportNoCustomServersHint,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),

            // Primary: paste / text input field
            TextField(
              controller: _uriController,
              decoration: InputDecoration(
                labelText: l10n.configImportPasteLink,
                hintText: 'vless://... | vmess://... | ss://...',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.content_paste),
                  tooltip: l10n.configImportFromClipboard,
                  onPressed: _pasteAndImport,
                ),
              ),
              keyboardType: TextInputType.url,
              onSubmitted: _importUri,
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _isImporting
                    ? null
                    : () => _importUri(_uriController.text.trim()),
                child: _isImporting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l10n.configImportImportButton),
              ),
            ),
            const SizedBox(height: 16),

            // Secondary: other import options
            OutlinedButton.icon(
              key: const Key('empty_state_import_button'),
              onPressed: widget.onImport,
              icon: const Icon(Icons.add),
              label: Text(l10n.configImportImportServerButton),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error View
// ---------------------------------------------------------------------------

class _ErrorView extends StatelessWidget {
  const _ErrorView({
    required this.error,
    required this.onRetry,
  });

  final String error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: 12),
            Text(
              l10n.configImportFailedToLoadServers,
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 8),
            Text(
              error,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 16),
            FilledButton.tonal(
              onPressed: onRetry,
              child: Text(l10n.retry),
            ),
          ],
        ),
      ),
    );
  }
}
