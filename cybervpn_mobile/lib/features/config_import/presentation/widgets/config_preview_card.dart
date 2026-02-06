import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';

/// Card widget for previewing imported VPN configuration details.
///
/// Displays configuration information including:
/// - Server name (remark)
/// - Server address and port
/// - Protocol badge (VLESS/VMess/Trojan/Shadowsocks)
/// - Transport type (optional)
/// - Security/TLS settings (optional)
///
/// Provides action buttons:
/// - Add Server (primary action)
/// - Cancel (secondary action)
///
/// Used in QR scanner and clipboard import flows.
class ConfigPreviewCard extends StatelessWidget {
  const ConfigPreviewCard({
    super.key,
    required this.config,
    required this.onAddServer,
    required this.onCancel,
    this.transportType,
    this.securityType,
  });

  /// The imported configuration to preview.
  final ImportedConfig config;

  /// Callback invoked when user taps "Add Server" button.
  final ValueChanged<ImportedConfig> onAddServer;

  /// Callback invoked when user taps "Cancel" button.
  final VoidCallback onCancel;

  /// Optional transport type (e.g., 'tcp', 'ws', 'grpc').
  final String? transportType;

  /// Optional security/TLS type (e.g., 'tls', 'reality', 'none').
  final String? securityType;

  /// Maps protocol to badge color.
  Color _getProtocolColor(String protocol, ColorScheme colorScheme) {
    final protocolLower = protocol.toLowerCase();
    switch (protocolLower) {
      case 'vless':
        return colorScheme.primary;
      case 'vmess':
        return colorScheme.secondary;
      case 'trojan':
        return colorScheme.error;
      case 'shadowsocks':
      case 'ss':
        return colorScheme.tertiary;
      default:
        return colorScheme.outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Card(
      margin: const EdgeInsets.all(16),
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Server name
            Text(
              config.name,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 16),

            // Server address and port
            _buildDetailRow(
              context,
              icon: Icons.dns,
              label: l10n.configImportAddressLabel,
              value: '${config.serverAddress}:${config.port}',
            ),
            const SizedBox(height: 12),

            // Protocol with badge
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.security,
                  size: 20,
                  color: colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.configImportProtocolLabel,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 4),
                      _ProtocolBadge(
                        protocol: config.protocol,
                        color: _getProtocolColor(config.protocol, colorScheme),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Transport type (if provided)
            if (transportType != null) ...[
              const SizedBox(height: 12),
              _buildDetailRow(
                context,
                icon: Icons.swap_horiz,
                label: l10n.configImportTransportLabel,
                value: transportType!.toUpperCase(),
              ),
            ],

            // Security type (if provided)
            if (securityType != null) ...[
              const SizedBox(height: 12),
              _buildDetailRow(
                context,
                icon: Icons.lock,
                label: l10n.configImportSecurityLabel,
                value: securityType!.toUpperCase(),
              ),
            ],

            const SizedBox(height: 24),

            // Action buttons
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                // Cancel button (secondary)
                TextButton(
                  onPressed: onCancel,
                  child: Text(l10n.cancel),
                ),
                const SizedBox(width: 12),

                // Add Server button (primary)
                ElevatedButton(
                  onPressed: () => onAddServer(config),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: colorScheme.primary,
                    foregroundColor: colorScheme.onPrimary,
                    minimumSize: const Size(120, 48),
                  ),
                  child: Text(l10n.configImportAddServerButton),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Builds a detail row with icon, label, and value.
  Widget _buildDetailRow(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
  }) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: 20,
          color: colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurface,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Protocol Badge Widget
// ---------------------------------------------------------------------------

/// Displays a color-coded protocol badge chip.
class _ProtocolBadge extends StatelessWidget {
  const _ProtocolBadge({
    required this.protocol,
    required this.color,
  });

  final String protocol;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color,
          width: 1.5,
        ),
      ),
      child: Text(
        protocol.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: color,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
