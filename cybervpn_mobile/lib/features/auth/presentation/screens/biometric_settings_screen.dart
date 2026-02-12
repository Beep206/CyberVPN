import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/shared/widgets/adaptive_switch.dart';
import 'package:cybervpn_mobile/features/auth/domain/services/app_lock_service.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show secureStorageProvider;

/// Screen for managing biometric authentication settings.
///
/// Allows users to:
/// - Enable/disable biometric login (using stored credentials)
/// - Enable/disable app lock (require biometric on resume)
/// - View available biometric types
class BiometricSettingsScreen extends ConsumerStatefulWidget {
  const BiometricSettingsScreen({super.key});

  @override
  ConsumerState<BiometricSettingsScreen> createState() =>
      _BiometricSettingsScreenState();
}

class _BiometricSettingsScreenState
    extends ConsumerState<BiometricSettingsScreen> {
  bool _biometricLoginEnabled = false;
  bool _appLockEnabled = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    unawaited(_loadSettings());
  }

  Future<void> _loadSettings() async {
    final biometricService = ref.read(biometricServiceProvider);
    final appLockService = ref.read(appLockServiceProvider);

    final biometricEnabled = await biometricService.isBiometricEnabled();
    final appLockEnabled = await appLockService.isAppLockEnabled();

    if (mounted) {
      setState(() {
        _biometricLoginEnabled = biometricEnabled;
        _appLockEnabled = appLockEnabled;
        _isLoading = false;
      });
    }
  }

  Future<void> _toggleBiometricLogin(bool value) async {
    // Trigger medium haptic on toggle switch change.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    if (value) {
      // Enabling - verify biometric first
      final biometricService = ref.read(biometricServiceProvider);
      final authenticated = await biometricService.authenticate(
        reason: AppLocalizations.of(context).biometricVerifyToEnableLogin,
      );

      if (!authenticated) {
        if (mounted) {
          // Trigger error haptic on authentication failure.
          unawaited(haptics.error());

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(AppLocalizations.of(context).biometricVerificationRequired),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
        return;
      }

      // Enroll device for biometric re-authentication using device-bound token.
      // The device token is obtained from the backend and stored securely.
      // No plaintext credentials are stored.
    } else {
      // Disabling - clear stored device token
      final storage = ref.read(secureStorageProvider);
      await storage.clearDeviceToken();
    }

    // Update setting
    final biometricService = ref.read(biometricServiceProvider);
    await biometricService.setBiometricEnabled(value);

    setState(() {
      _biometricLoginEnabled = value;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            value
                ? AppLocalizations.of(context).biometricLoginEnabled
                : AppLocalizations.of(context).biometricLoginDisabled,
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }



  Future<void> _toggleAppLock(bool value) async {
    // Trigger medium haptic on toggle switch change.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    if (value) {
      // Enabling - verify biometric first
      final biometricService = ref.read(biometricServiceProvider);
      final authenticated = await biometricService.authenticate(
        reason: AppLocalizations.of(context).biometricVerifyToEnableAppLock,
      );

      if (!authenticated) {
        if (mounted) {
          // Trigger error haptic on authentication failure.
          unawaited(haptics.error());

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(AppLocalizations.of(context).biometricVerificationRequired),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
        return;
      }
    }

    // Update setting
    final appLockService = ref.read(appLockServiceProvider);
    await appLockService.setAppLockEnabled(value);

    setState(() {
      _appLockEnabled = value;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            value ? AppLocalizations.of(context).biometricAppLockEnabled : AppLocalizations.of(context).biometricAppLockDisabled,
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final biometricAvailable = ref.watch(isBiometricAvailableProvider);
    final biometricTypes = ref.watch(availableBiometricsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context).biometricSettingsTitle),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Biometric availability info
                biometricAvailable.when(
                  data: (available) {
                    if (!available) {
                      return _BiometricUnavailableCard();
                    }
                    return _BiometricInfoCard(biometricTypes: biometricTypes);
                  },
                  loading: () => const Center(
                    child: CircularProgressIndicator(),
                  ),
                  error: (_, _) => _BiometricUnavailableCard(),
                ),
                const SizedBox(height: 24),

                // Settings section
                Text(
                  AppLocalizations.of(context).biometricAuthSection,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),

                // Biometric Login toggle
                biometricAvailable.when(
                  data: (available) => _SettingsTile(
                    icon: Icons.fingerprint,
                    title: AppLocalizations.of(context).biometricLoginLabel,
                    subtitle: AppLocalizations.of(context).biometricLoginDescription,
                    value: _biometricLoginEnabled,
                    onChanged: available ? _toggleBiometricLogin : null,
                    disabled: !available,
                  ),
                  loading: () => _SettingsTile(
                    icon: Icons.fingerprint,
                    title: AppLocalizations.of(context).biometricLoginLabel,
                    subtitle: AppLocalizations.of(context).biometricLoadingState,
                    value: false,
                    onChanged: null,
                    disabled: true,
                  ),
                  error: (_, _) => _SettingsTile(
                    icon: Icons.fingerprint,
                    title: AppLocalizations.of(context).biometricLoginLabel,
                    subtitle: AppLocalizations.of(context).biometricUnavailableState,
                    value: false,
                    onChanged: null,
                    disabled: true,
                  ),
                ),
                const SizedBox(height: 8),

                // App Lock toggle
                biometricAvailable.when(
                  data: (available) => _SettingsTile(
                    icon: Icons.lock_outline,
                    title: AppLocalizations.of(context).biometricAppLockLabel,
                    subtitle: AppLocalizations.of(context).biometricAppLockDescription,
                    value: _appLockEnabled,
                    onChanged: available ? _toggleAppLock : null,
                    disabled: !available,
                  ),
                  loading: () => _SettingsTile(
                    icon: Icons.lock_outline,
                    title: AppLocalizations.of(context).biometricAppLockLabel,
                    subtitle: AppLocalizations.of(context).biometricLoadingState,
                    value: false,
                    onChanged: null,
                    disabled: true,
                  ),
                  error: (_, _) => _SettingsTile(
                    icon: Icons.lock_outline,
                    title: AppLocalizations.of(context).biometricAppLockLabel,
                    subtitle: AppLocalizations.of(context).biometricUnavailableState,
                    value: false,
                    onChanged: null,
                    disabled: true,
                  ),
                ),
              ],
            ),
    );
  }
}

class _BiometricUnavailableCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final l10n = AppLocalizations.of(context);
    return Semantics(
      label: '${l10n.biometricUnavailableTitle}. ${l10n.biometricUnavailableMessage}',
      child: Card(
        color: theme.colorScheme.errorContainer,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(
                Icons.warning_amber_rounded,
                color: theme.colorScheme.onErrorContainer,
                semanticLabel: '', // Handled by parent Semantics
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ExcludeSemantics(
                      child: Text(
                        l10n.biometricUnavailableTitle,
                        style: theme.textTheme.titleSmall?.copyWith(
                          color: theme.colorScheme.onErrorContainer,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    ExcludeSemantics(
                      child: Text(
                        l10n.biometricUnavailableMessage,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onErrorContainer,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BiometricInfoCard extends StatelessWidget {
  final AsyncValue<List<BiometricType>> biometricTypes;

  const _BiometricInfoCard({required this.biometricTypes});

  String _getBiometricLabel(BuildContext context, List<BiometricType> types) {
    if (types.contains(BiometricType.face)) {
      return 'Face ID';
    }
    if (types.contains(BiometricType.fingerprint) ||
        types.contains(BiometricType.strong)) {
      return AppLocalizations.of(context).biometricLabelFingerprint;
    }
    if (types.contains(BiometricType.iris)) {
      return 'Iris';
    }
    return AppLocalizations.of(context).biometricLabelGeneric;
  }

  IconData _getBiometricIcon(List<BiometricType> types) {
    if (types.contains(BiometricType.face)) {
      return Icons.face;
    }
    return Icons.fingerprint;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final l10n = AppLocalizations.of(context);
    return biometricTypes.when(
      data: (types) {
        final label = _getBiometricLabel(context, types);
        return Semantics(
          label: '$label ${l10n.biometricAvailableOnDevice}',
          child: Card(
            color: theme.colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(
                    _getBiometricIcon(types),
                    size: 40,
                    color: theme.colorScheme.onPrimaryContainer,
                    semanticLabel: '', // Handled by parent Semantics
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        ExcludeSemantics(
                          child: Text(
                            label,
                            style: theme.textTheme.titleSmall?.copyWith(
                              color: theme.colorScheme.onPrimaryContainer,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        ExcludeSemantics(
                          child: Text(
                            l10n.biometricAvailableOnDevice,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onPrimaryContainer,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    Icons.check_circle,
                    color: theme.colorScheme.onPrimaryContainer,
                    semanticLabel: '', // Handled by parent Semantics
                  ),
                ],
              ),
            ),
          ),
        );
      },
      loading: () => Semantics(
        label: l10n.biometricLoadingState,
        child: const Card(
          child: Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          ),
        ),
      ),
      error: (_, _) => _BiometricUnavailableCard(),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool>? onChanged;
  final bool disabled;

  const _SettingsTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
    this.disabled = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Semantics(
      label: title,
      hint: subtitle,
      toggled: value,
      enabled: !disabled,
      child: Card(
        child: ListTile(
          leading: Icon(
            icon,
            color: disabled
                ? theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5)
                : theme.colorScheme.primary,
            semanticLabel: '', // Handled by Semantics wrapper
          ),
          title: ExcludeSemantics(
            child: Text(
              title,
              style: TextStyle(
                color: disabled
                    ? theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5)
                    : null,
              ),
            ),
          ),
          subtitle: ExcludeSemantics(
            child: Text(
              subtitle,
              style: TextStyle(
                color: disabled
                    ? theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5)
                    : null,
              ),
            ),
          ),
          trailing: ExcludeSemantics(
            child: AdaptiveSwitch(
              value: value,
              onChanged: disabled ? null : onChanged,
            ),
          ),
          enabled: !disabled,
        ),
      ),
    );
  }
}
