import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';

// ---------------------------------------------------------------------------
// DevicesScreen
// ---------------------------------------------------------------------------

/// Device management screen displaying connected devices with ability to
/// remove non-current devices.
///
/// Features:
/// - Lists all devices from profile API with name, OS, last connected, status
/// - Current device has 'This device' badge and cannot be removed
/// - Other devices can be removed with swipe-to-delete or delete button
/// - Confirmation dialog before device removal
/// - Warning banner when device limit is reached
class DevicesScreen extends ConsumerStatefulWidget {
  const DevicesScreen({super.key});

  @override
  ConsumerState<DevicesScreen> createState() => _DevicesScreenState();
}

class _DevicesScreenState extends ConsumerState<DevicesScreen> {
  String? _currentDeviceId;
  bool _isLoadingDeviceInfo = true;

  @override
  void initState() {
    super.initState();
    _loadCurrentDeviceId();
  }

  /// Load the current device ID to mark it in the list
  Future<void> _loadCurrentDeviceId() async {
    try {
      final deviceInfo = DeviceInfoPlugin();
      String? deviceId;

      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        deviceId = androidInfo.id; // Android ID
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        deviceId = iosInfo.identifierForVendor; // iOS vendor ID
      }

      if (mounted) {
        setState(() {
          _currentDeviceId = deviceId;
          _isLoadingDeviceInfo = false;
        });
      }
    } catch (e, st) {
      AppLogger.error('Failed to load device ID', error: e, stackTrace: st);
      if (mounted) {
        setState(() {
          _isLoadingDeviceInfo = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncProfile = ref.watch(profileProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Device Management'),
      ),
      body: asyncProfile.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorBody(
          message: error.toString(),
          onRetry: () => ref.invalidate(profileProvider),
        ),
        data: (profileState) {
          final devices = profileState.devices;

          if (_isLoadingDeviceInfo) {
            return const Center(child: CircularProgressIndicator());
          }

          return RefreshIndicator(
            onRefresh: () async {
              await ref.read(profileProvider.notifier).refreshProfile();
            },
            child: ListView(
              padding: const EdgeInsets.all(Spacing.md),
              children: [
                // Warning banner if device limit reached
                // Assuming max 5 devices (this should come from backend)
                if (devices.length >= 5) ...[
                  _DeviceLimitWarning(),
                  const SizedBox(height: Spacing.md),
                ],

                // Device count header
                Text(
                  '${devices.length} ${devices.length == 1 ? 'device' : 'devices'} connected',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: Spacing.md),

                // Device list
                if (devices.isEmpty)
                  const _EmptyDeviceList()
                else
                  ...devices.map((device) {
                    final isCurrent = _isCurrentDevice(device);
                    return _DeviceCard(
                      key: Key('device_${device.id}'),
                      device: device,
                      isCurrent: isCurrent,
                      currentDeviceId: _currentDeviceId ?? '',
                      onRemove: isCurrent ? null : () => _showRemoveDialog(device),
                    );
                  }),

                // Bottom padding for safe area
                const SizedBox(height: 80),
              ],
            ),
          );
        },
      ),
    );
  }

  /// Check if a device is the current device
  bool _isCurrentDevice(Device device) {
    // First check if the device entity has isCurrent flag set by backend
    if (device.isCurrent) return true;

    // Fallback: compare with locally detected device ID
    if (_currentDeviceId != null && device.id == _currentDeviceId) {
      return true;
    }

    return false;
  }

  /// Show confirmation dialog before removing device
  Future<void> _showRemoveDialog(Device device) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove Device'),
        content: Text(
          'Remove ${device.name}?\n\n'
          'You\'ll need to log in again on this device if you want to use it later.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await _removeDevice(device);
    }
  }

  /// Remove a device via API and update state
  Future<void> _removeDevice(Device device) async {
    try {
      // Show loading indicator
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Removing device...'),
            duration: Duration(seconds: 1),
          ),
        );
      }

      // Call removeDevice method on ProfileNotifier
      await ref.read(profileProvider.notifier).removeDevice(
            deviceId: device.id,
            currentDeviceId: _currentDeviceId ?? '',
          );

      if (mounted) {
        HapticFeedback.lightImpact();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${device.name} removed successfully'),
            backgroundColor: CyberColors.matrixGreen,
          ),
        );
      }
    } catch (e, st) {
      AppLogger.error('Failed to remove device', error: e, stackTrace: st);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to remove device: ${e.toString()}'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Device Limit Warning Banner
// ---------------------------------------------------------------------------

class _DeviceLimitWarning extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: const Color(0xFFFF5252).withAlpha(25),
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: const Color(0xFFFF5252).withAlpha(80),
        ),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.warning_amber_rounded,
            color: Color(0xFFFF5252),
          ),
          const SizedBox(width: Spacing.md),
          Expanded(
            child: Text(
              'Device limit reached. Remove a device to add new ones.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFFFF5252),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Device Card
// ---------------------------------------------------------------------------

class _DeviceCard extends StatelessWidget {
  const _DeviceCard({
    super.key,
    required this.device,
    required this.isCurrent,
    required this.currentDeviceId,
    this.onRemove,
  });

  final Device device;
  final bool isCurrent;
  final String currentDeviceId;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    // Format last active time
    final lastActiveText = device.lastActiveAt != null
        ? _formatLastActive(device.lastActiveAt!)
        : 'Never';

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.sm),
      child: Dismissible(
        key: Key('dismissible_${device.id}'),
        // Only allow swipe-to-delete for non-current devices
        confirmDismiss: isCurrent
            ? null
            : (direction) async {
                // Show confirmation dialog
                return await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Remove Device'),
                    content: Text(
                      'Remove ${device.name}?\n\n'
                      'You\'ll need to log in again on this device.',
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(false),
                        child: const Text('Cancel'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.of(context).pop(true),
                        style: FilledButton.styleFrom(
                          backgroundColor: colorScheme.error,
                        ),
                        child: const Text('Remove'),
                      ),
                    ],
                  ),
                );
              },
        onDismissed: isCurrent ? null : (direction) => onRemove?.call(),
        direction: isCurrent ? DismissDirection.none : DismissDirection.endToStart,
        background: Container(
          alignment: AlignmentDirectional.centerEnd,
          padding: const EdgeInsetsDirectional.only(end: Spacing.md),
          decoration: BoxDecoration(
            color: colorScheme.error,
            borderRadius: BorderRadius.circular(Radii.md),
          ),
          child: const Icon(Icons.delete_outline, color: Colors.white),
        ),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(Spacing.md),
            child: Row(
              children: [
                // Device icon
                Container(
                  padding: const EdgeInsets.all(Spacing.sm),
                  decoration: BoxDecoration(
                    color: colorScheme.primary.withAlpha(25),
                    borderRadius: BorderRadius.circular(Radii.sm),
                  ),
                  child: Icon(
                    _getDeviceIcon(device.platform),
                    size: 24,
                    color: colorScheme.primary,
                  ),
                ),
                const SizedBox(width: Spacing.md),

                // Device info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Device name with optional badge
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              device.name,
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (isCurrent) ...[
                            const SizedBox(width: Spacing.sm),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: Spacing.sm,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: CyberColors.matrixGreen.withAlpha(40),
                                borderRadius: BorderRadius.circular(Radii.sm),
                              ),
                              child: Text(
                                'This device',
                                style: theme.textTheme.labelSmall?.copyWith(
                                  color: CyberColors.matrixGreen,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: Spacing.xs),

                      // Platform and last active
                      Row(
                        children: [
                          Icon(
                            Icons.smartphone_outlined,
                            size: 14,
                            color: colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: Spacing.xs),
                          Text(
                            device.platform,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                          const SizedBox(width: Spacing.md),
                          Icon(
                            Icons.access_time,
                            size: 14,
                            color: colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: Spacing.xs),
                          Text(
                            lastActiveText,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),

                      // IP address if available
                      if (device.ipAddress != null) ...[
                        const SizedBox(height: Spacing.xs),
                        Row(
                          children: [
                            Icon(
                              Icons.wifi_outlined,
                              size: 14,
                              color: colorScheme.onSurfaceVariant,
                            ),
                            const SizedBox(width: Spacing.xs),
                            Text(
                              device.ipAddress!,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: colorScheme.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),

                // Delete button for non-current devices
                if (!isCurrent && onRemove != null)
                  IconButton(
                    key: Key('delete_btn_${device.id}'),
                    icon: Icon(Icons.delete_outline, color: colorScheme.error),
                    onPressed: onRemove,
                    tooltip: 'Remove device',
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Get appropriate icon based on platform
  IconData _getDeviceIcon(String platform) {
    final platformLower = platform.toLowerCase();
    if (platformLower.contains('ios') || platformLower.contains('iphone')) {
      return Icons.phone_iphone;
    } else if (platformLower.contains('android')) {
      return Icons.phone_android;
    } else if (platformLower.contains('windows')) {
      return Icons.computer;
    } else if (platformLower.contains('mac') || platformLower.contains('macos')) {
      return Icons.laptop_mac;
    } else if (platformLower.contains('linux')) {
      return Icons.computer;
    } else if (platformLower.contains('web')) {
      return Icons.language;
    }
    return Icons.devices;
  }

  /// Format last active timestamp
  String _formatLastActive(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat.yMMMd().format(dateTime);
    }
  }
}

// ---------------------------------------------------------------------------
// Empty Device List
// ---------------------------------------------------------------------------

class _EmptyDeviceList extends StatelessWidget {
  const _EmptyDeviceList();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.devices_outlined,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withAlpha(100),
            ),
            const SizedBox(height: Spacing.md),
            Text(
              'No devices connected',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              'Connect to VPN to register this device',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant.withAlpha(180),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
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
