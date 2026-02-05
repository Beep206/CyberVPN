import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/features/auth/domain/services/app_lock_service.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart'
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
    _loadSettings();
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
    if (value) {
      // Enabling - verify biometric first
      final biometricService = ref.read(biometricServiceProvider);
      final authenticated = await biometricService.authenticate(
        reason: 'Verify to enable biometric login',
      );

      if (!authenticated) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Biometric verification required'),
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
        return;
      }

      // Prompt for credentials to store
      if (mounted) {
        final credentials = await _showCredentialsDialog();
        if (credentials == null) return;

        // Store credentials
        final storage = ref.read(secureStorageProvider);
        await storage.setBiometricCredentials(
          email: credentials.email,
          password: credentials.password,
        );
      }
    } else {
      // Disabling - clear stored credentials
      final storage = ref.read(secureStorageProvider);
      await storage.clearBiometricCredentials();
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
                ? 'Biometric login enabled'
                : 'Biometric login disabled',
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<({String email, String password})?> _showCredentialsDialog() async {
    final emailController = TextEditingController();
    final passwordController = TextEditingController();

    return showDialog<({String email, String password})>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Enter credentials'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Enter your login credentials to enable quick sign-in with biometrics.',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: emailController,
              decoration: const InputDecoration(
                labelText: 'Email',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: passwordController,
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
              autofillHints: const [AutofillHints.password],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(null),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final email = emailController.text.trim();
              final password = passwordController.text;
              if (email.isNotEmpty && password.isNotEmpty) {
                Navigator.of(context).pop((email: email, password: password));
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Future<void> _toggleAppLock(bool value) async {
    if (value) {
      // Enabling - verify biometric first
      final biometricService = ref.read(biometricServiceProvider);
      final authenticated = await biometricService.authenticate(
        reason: 'Verify to enable app lock',
      );

      if (!authenticated) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Biometric verification required'),
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
            value ? 'App lock enabled' : 'App lock disabled',
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
        title: const Text('Security'),
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
                  error: (_, __) => _BiometricUnavailableCard(),
                ),
                const SizedBox(height: 24),

                // Settings section
                Text(
                  'Biometric Authentication',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),

                // Biometric Login toggle
                biometricAvailable.when(
                  data: (available) => _SettingsTile(
                    icon: Icons.fingerprint,
                    title: 'Biometric Login',
                    subtitle: 'Use biometrics to sign in quickly',
                    value: _biometricLoginEnabled,
                    onChanged: available ? _toggleBiometricLogin : null,
                    disabled: !available,
                  ),
                  loading: () => _SettingsTile(
                    icon: Icons.fingerprint,
                    title: 'Biometric Login',
                    subtitle: 'Loading...',
                    value: false,
                    onChanged: null,
                    disabled: true,
                  ),
                  error: (_, __) => _SettingsTile(
                    icon: Icons.fingerprint,
                    title: 'Biometric Login',
                    subtitle: 'Unavailable',
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
                    title: 'App Lock',
                    subtitle:
                        'Require biometrics when returning to app (30+ seconds)',
                    value: _appLockEnabled,
                    onChanged: available ? _toggleAppLock : null,
                    disabled: !available,
                  ),
                  loading: () => _SettingsTile(
                    icon: Icons.lock_outline,
                    title: 'App Lock',
                    subtitle: 'Loading...',
                    value: false,
                    onChanged: null,
                    disabled: true,
                  ),
                  error: (_, __) => _SettingsTile(
                    icon: Icons.lock_outline,
                    title: 'App Lock',
                    subtitle: 'Unavailable',
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

    return Card(
      color: theme.colorScheme.errorContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              Icons.warning_amber_rounded,
              color: theme.colorScheme.onErrorContainer,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Biometrics Unavailable',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.onErrorContainer,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Your device does not support biometric authentication, '
                    'or no biometrics are enrolled.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onErrorContainer,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BiometricInfoCard extends StatelessWidget {
  final AsyncValue<List<BiometricType>> biometricTypes;

  const _BiometricInfoCard({required this.biometricTypes});

  String _getBiometricLabel(List<BiometricType> types) {
    if (types.contains(BiometricType.face)) {
      return 'Face ID';
    }
    if (types.contains(BiometricType.fingerprint) ||
        types.contains(BiometricType.strong)) {
      return 'Fingerprint';
    }
    if (types.contains(BiometricType.iris)) {
      return 'Iris';
    }
    return 'Biometrics';
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

    return biometricTypes.when(
      data: (types) => Card(
        color: theme.colorScheme.primaryContainer,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(
                _getBiometricIcon(types),
                size: 40,
                color: theme.colorScheme.onPrimaryContainer,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _getBiometricLabel(types),
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Available on this device',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.check_circle,
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ],
          ),
        ),
      ),
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Center(child: CircularProgressIndicator()),
        ),
      ),
      error: (_, __) => _BiometricUnavailableCard(),
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

    return Card(
      child: ListTile(
        leading: Icon(
          icon,
          color: disabled
              ? theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5)
              : theme.colorScheme.primary,
        ),
        title: Text(
          title,
          style: TextStyle(
            color: disabled
                ? theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5)
                : null,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: TextStyle(
            color: disabled
                ? theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5)
                : null,
          ),
        ),
        trailing: Switch(
          value: value,
          onChanged: disabled ? null : onChanged,
        ),
        enabled: !disabled,
      ),
    );
  }
}
