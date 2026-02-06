import 'package:flutter/material.dart';
import 'dart:async';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';

class AppLockScreen extends StatefulWidget {
  final BiometricService biometricService;
  final VoidCallback onUnlocked;

  const AppLockScreen({super.key, required this.biometricService, required this.onUnlocked});

  @override
  State<AppLockScreen> createState() => _AppLockScreenState();
}

class _AppLockScreenState extends State<AppLockScreen> {
  bool _isAuthenticating = false;

  @override
  void initState() {
    super.initState();
    unawaited(_authenticate());
  }

  Future<void> _authenticate() async {
    if (_isAuthenticating) return;
    setState(() => _isAuthenticating = true);
    try {
      final success = await widget.biometricService.authenticate(reason: 'Unlock CyberVPN');
      if (success && mounted) {
        widget.onUnlocked();
      }
    } finally {
      if (mounted) setState(() => _isAuthenticating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.lock_outline, size: 80, color: theme.colorScheme.primary),
            const SizedBox(height: 24),
            Text(l10n.appLockTitle, style: theme.textTheme.headlineMedium),
            const SizedBox(height: 8),
            Text(l10n.appLockSubtitle, style: theme.textTheme.bodyLarge),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: _isAuthenticating ? null : _authenticate,
              icon: const Icon(Icons.fingerprint),
              label: Text(l10n.appLockUnlockButton),
            ),
          ],
        ),
      ),
    );
  }
}
