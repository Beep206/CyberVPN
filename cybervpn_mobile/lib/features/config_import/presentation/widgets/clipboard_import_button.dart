import 'dart:convert';
import 'dart:async';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// Detected Config Model
// ---------------------------------------------------------------------------

/// Represents a detected VPN configuration from clipboard.
class DetectedConfig {
  const DetectedConfig({
    required this.uri,
    required this.preview,
  });

  /// The full VPN URI
  final String uri;

  /// A user-friendly preview of the config (first 50 chars or parsed name)
  final String preview;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DetectedConfig &&
          runtimeType == other.runtimeType &&
          uri == other.uri;

  @override
  int get hashCode => uri.hashCode;

  @override
  String toString() => 'DetectedConfig(uri: $uri, preview: $preview)';
}

// ---------------------------------------------------------------------------
// Clipboard Import Observer Widget
// ---------------------------------------------------------------------------

/// A widget that monitors app lifecycle and automatically detects VPN configs
/// in the clipboard when the app resumes from background.
///
/// This widget implements [WidgetsBindingObserver] to listen for
/// [AppLifecycleState.resumed] events. When the app resumes and the
/// `clipboardAutoDetect` setting is enabled, it checks the clipboard for
/// VPN URIs and shows a bottom sheet for user confirmation.
///
/// Features:
/// - Detects vless://, vmess://, trojan://, ss://, https:// URIs
/// - Supports multi-line clipboard content (multiple configs)
/// - Tracks last imported content hash to avoid repeated prompts
/// - Debounces clipboard checks to prevent rapid-fire checks
///
/// Usage:
/// ```dart
/// ClipboardImportObserver(
///   child: YourAppWidget(),
/// )
/// ```
class ClipboardImportObserver extends ConsumerStatefulWidget {
  const ClipboardImportObserver({
    required this.child,
    super.key,
  });

  /// The child widget to wrap.
  final Widget child;

  @override
  ConsumerState<ClipboardImportObserver> createState() =>
      _ClipboardImportObserverState();
}

class _ClipboardImportObserverState
    extends ConsumerState<ClipboardImportObserver> with WidgetsBindingObserver {
  /// Hash of the last clipboard content that was processed to avoid
  /// showing the same bottom sheet multiple times.
  String? _lastClipboardHash;

  /// Timestamp of the last clipboard check for debouncing.
  DateTime? _lastCheckTime;

  /// Minimum duration between clipboard checks (debounce).
  static const _debounceDelay = Duration(seconds: 2);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);

    // Only check clipboard when app resumes from background
    if (state == AppLifecycleState.resumed) {
      unawaited(_checkClipboardOnResume());
    }
  }

  /// Check clipboard when app resumes and show bottom sheet if configs detected.
  Future<void> _checkClipboardOnResume() async {
    try {
      // Debounce: Don't check if we checked very recently
      final now = DateTime.now();
      if (_lastCheckTime != null &&
          now.difference(_lastCheckTime!) < _debounceDelay) {
        AppLogger.debug(
          'Clipboard check debounced',
          category: 'clipboard_import',
        );
        return;
      }
      _lastCheckTime = now;

      // Check if clipboard auto-detect is enabled in settings
      final settings = ref.read(settingsProvider).value;
      if (settings == null || !settings.clipboardAutoDetect) {
        AppLogger.debug(
          'Clipboard auto-detect disabled in settings',
          category: 'clipboard_import',
        );
        return;
      }

      // Read clipboard content
      final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
      final text = clipboardData?.text?.trim();

      if (text == null || text.isEmpty) {
        AppLogger.debug(
          'Clipboard is empty or null',
          category: 'clipboard_import',
        );
        return;
      }

      // Calculate hash of clipboard content
      final contentHash = _calculateHash(text);

      // Don't show sheet again if we've already processed this exact content
      if (contentHash == _lastClipboardHash) {
        AppLogger.debug(
          'Clipboard content already processed (hash match)',
          category: 'clipboard_import',
        );
        return;
      }

      // Detect VPN configs in clipboard
      final detectedConfigs = _detectVpnConfigs(text);

      if (detectedConfigs.isEmpty) {
        AppLogger.debug(
          'No VPN configs detected in clipboard',
          category: 'clipboard_import',
        );
        return;
      }

      // Update last processed hash
      _lastClipboardHash = contentHash;

      // Show bottom sheet with detected configs
      if (mounted && context.mounted) {
        _showImportBottomSheet(detectedConfigs);
      }
    } catch (e, st) {
      AppLogger.error(
        'Failed to check clipboard on resume',
        error: e,
        stackTrace: st,
        category: 'clipboard_import',
      );
    }
  }

  /// Calculate SHA-256 hash of clipboard content for deduplication.
  String _calculateHash(String content) {
    final bytes = utf8.encode(content);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  /// Detect VPN configuration URIs in the given text.
  ///
  /// Supports:
  /// - vless://
  /// - vmess://
  /// - trojan://
  /// - ss:// (Shadowsocks)
  /// - https:// (subscription URLs)
  ///
  /// Returns a list of [DetectedConfig] objects with URI and preview text.
  List<DetectedConfig> _detectVpnConfigs(String text) {
    final configs = <DetectedConfig>[];

    // Supported URI schemes
    final supportedSchemes = [
      ...ParseVpnUri.supportedSchemes, // vless://, vmess://, trojan://, ss://
      'https://', // subscription URLs
    ];

    // Split by newlines to support multi-line clipboard content
    final lines = text.split('\n');

    for (final line in lines) {
      final trimmedLine = line.trim();
      if (trimmedLine.isEmpty) continue;

      // Check if line starts with any supported scheme
      final lowerLine = trimmedLine.toLowerCase();
      for (final scheme in supportedSchemes) {
        if (lowerLine.startsWith(scheme)) {
          // Create preview: first 50 chars or try to extract server name
          final preview = _createPreview(trimmedLine);
          configs.add(DetectedConfig(uri: trimmedLine, preview: preview));
          break; // Only add once per line
        }
      }
    }

    AppLogger.info(
      'Detected ${configs.length} VPN config(s) in clipboard',
      category: 'clipboard_import',
    );

    return configs;
  }

  /// Create a user-friendly preview of a VPN config URI.
  ///
  /// Returns the first 50 characters with ellipsis, or attempts to extract
  /// a server name/address if available in the URI.
  String _createPreview(String uri) {
    // Simple preview: first 50 chars
    if (uri.length <= 50) {
      return uri;
    }
    return '${uri.substring(0, 50)}...';
  }

  /// Show bottom sheet with detected configs and import options.
  void _showImportBottomSheet(List<DetectedConfig> configs) {
    unawaited(showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _ClipboardImportBottomSheet(
        detectedConfigs: configs,
        onImport: () => _handleImport(configs),
        onDismiss: _handleDismiss,
        onDontAskAgain: _handleDontAskAgain,
      ),
    ));
  }

  /// Handle import action: import all detected configs.
  Future<void> _handleImport(List<DetectedConfig> configs) async {
    // Close bottom sheet
    if (mounted && context.mounted) {
      Navigator.of(context).pop();
    }

    AppLogger.info(
      'Import initiated for ${configs.length} config(s)',
      category: 'clipboard_import',
    );

    int successCount = 0;
    int failureCount = 0;
    final errors = <String>[];

    // Import each detected config
    for (final config in configs) {
      try {
        final importedConfig = await ref
            .read(configImportProvider.notifier)
            .importFromUri(
              config.uri,
              source: ImportSource.clipboard,
            );

        if (importedConfig != null) {
          successCount++;
        } else {
          failureCount++;
          errors.add('Failed to import: ${config.preview}');
        }
      } catch (e) {
        failureCount++;
        errors.add('Error importing ${config.preview}: $e');
        AppLogger.error(
          'Failed to import config from clipboard',
          error: e,
          category: 'clipboard_import',
        );
      }
    }

    // Trigger haptic feedback based on result
    final haptics = ref.read(hapticServiceProvider);
    if (successCount > 0 && failureCount == 0) {
      // All succeeded - success haptic
      unawaited(haptics.success());
    } else if (successCount > 0 && failureCount > 0) {
      // Partial success - impact haptic
      unawaited(haptics.impact());
    } else {
      // All failed - error haptic
      unawaited(haptics.error());
    }

    // Show result snackbar
    if (mounted && context.mounted) {
      final messenger = ScaffoldMessenger.of(context);

      if (successCount > 0 && failureCount == 0) {
        // All succeeded
        messenger.showSnackBar(
          SnackBar(
            content: Text(
              successCount == 1
                  ? 'Successfully imported 1 config'
                  : 'Successfully imported $successCount configs',
            ),
            backgroundColor: Theme.of(context).colorScheme.primary,
          ),
        );
      } else if (successCount > 0 && failureCount > 0) {
        // Partial success
        messenger.showSnackBar(
          SnackBar(
            content: Text(
              'Imported $successCount config(s), $failureCount failed',
            ),
            backgroundColor: Theme.of(context).colorScheme.tertiary,
            duration: const Duration(seconds: 4),
          ),
        );
      } else {
        // All failed
        messenger.showSnackBar(
          SnackBar(
            content: Text(
              failureCount == 1
                  ? 'Failed to import config'
                  : 'Failed to import $failureCount configs',
            ),
            backgroundColor: Theme.of(context).colorScheme.error,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }

    AppLogger.info(
      'Clipboard import completed: $successCount success, $failureCount failed',
      category: 'clipboard_import',
    );
  }

  /// Handle dismiss action: close bottom sheet without import.
  void _handleDismiss() {
    if (mounted && context.mounted) {
      Navigator.of(context).pop();
    }
    AppLogger.debug('Clipboard import dismissed', category: 'clipboard_import');
  }

  /// Handle "Don't ask again" action: disable clipboard auto-detect.
  Future<void> _handleDontAskAgain() async {
    // Close bottom sheet
    if (mounted && context.mounted) {
      Navigator.of(context).pop();
    }

    // Update settings to disable clipboard auto-detect
    try {
      await ref
          .read(settingsProvider.notifier)
          .toggleClipboardAutoDetect();
      AppLogger.info(
        'Clipboard auto-detect disabled',
        category: 'clipboard_import',
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to update clipboard auto-detect setting',
        error: e,
        stackTrace: st,
        category: 'clipboard_import',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    // Simply wrap the child - all logic is in lifecycle observer
    return widget.child;
  }
}

// ---------------------------------------------------------------------------
// Clipboard Import Bottom Sheet Widget
// ---------------------------------------------------------------------------

/// Bottom sheet UI for clipboard import confirmation.
///
/// Displays detected configs with preview, and provides Import, Dismiss,
/// and "Don't ask again" actions.
class _ClipboardImportBottomSheet extends StatelessWidget {
  const _ClipboardImportBottomSheet({
    required this.detectedConfigs,
    required this.onImport,
    required this.onDismiss,
    required this.onDontAskAgain,
  });

  final List<DetectedConfig> detectedConfigs;
  final VoidCallback onImport;
  final VoidCallback onDismiss;
  final VoidCallback onDontAskAgain;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        border: Border.all(
          color: colorScheme.primary.withAlpha((0.3 * 255).toInt()),
          width: 1,
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Drag handle
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: colorScheme.onSurface.withAlpha((0.2 * 255).toInt()),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // Title
              Text(
                'VPN Config Detected',
                style: theme.textTheme.titleLarge?.copyWith(
                  color: colorScheme.primary,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),

              // Subtitle
              Text(
                detectedConfigs.length == 1
                    ? 'Found 1 VPN configuration in your clipboard'
                    : 'Found ${detectedConfigs.length} VPN configurations in your clipboard',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurface.withAlpha((0.7 * 255).toInt()),
                ),
              ),
              const SizedBox(height: 20),

              // Config preview list (scrollable if many)
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 200),
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: detectedConfigs.length,
                  separatorBuilder: (context, index) =>
                      const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final config = detectedConfigs[index];
                    return Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: colorScheme.outline.withAlpha((0.3 * 255).toInt()),
                        ),
                      ),
                      child: Text(
                        config.preview,
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontFamily: 'monospace',
                          color: colorScheme.onSurface,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),

              // Import button
              FilledButton(
                onPressed: onImport,
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: Text(
                  detectedConfigs.length == 1
                      ? 'Import Config'
                      : 'Import All (${detectedConfigs.length})',
                ),
              ),
              const SizedBox(height: 12),

              // Dismiss button
              OutlinedButton(
                onPressed: onDismiss,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text('Dismiss'),
              ),
              const SizedBox(height: 12),

              // "Don't ask again" button
              TextButton(
                onPressed: onDontAskAgain,
                child: Text(
                  "Don't ask again",
                  style: TextStyle(
                    color: colorScheme.error,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
