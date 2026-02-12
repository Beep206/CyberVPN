import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';

// ---------------------------------------------------------------------------
// TrialCard
// ---------------------------------------------------------------------------

/// Displays trial eligibility and activation status.
///
/// Shows "7-Day Free Trial" with "Start Trial" button if user is eligible.
/// If trial is active, shows badge with days remaining.
class TrialCard extends ConsumerStatefulWidget {
  const TrialCard({super.key});

  @override
  ConsumerState<TrialCard> createState() => _TrialCardState();
}

class _TrialCardState extends ConsumerState<TrialCard> {
  bool _isLoading = true;
  bool _isEligible = false;
  int? _daysRemaining;
  bool _trialUsed = false;
  bool _isActivating = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    unawaited(_fetchTrialStatus());
  }

  Future<void> _fetchTrialStatus() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final repo = ref.read(subscriptionRepositoryProvider);
    final result = await repo.getTrialStatus();

    if (!mounted) return;

    switch (result) {
      case Success(:final data):
        setState(() {
          _isEligible = data['is_eligible'] as bool? ?? false;
          _daysRemaining = data['days_remaining'] as int?;
          _trialUsed = data['trial_used'] as bool? ?? false;
          _isLoading = false;
        });
      case Failure(:final failure):
        setState(() {
          _errorMessage = failure.message;
          _isLoading = false;
        });
    }
  }

  Future<void> _activateTrial() async {
    setState(() {
      _isActivating = true;
      _errorMessage = null;
    });

    final repo = ref.read(subscriptionRepositoryProvider);
    final result = await repo.activateTrial();

    if (!mounted) return;

    switch (result) {
      case Success():
        // Show success message
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(AppLocalizations.of(context).subscriptionTrialActivated),
              backgroundColor: CyberColors.matrixGreen,
            ),
          );
        }
        // Refresh trial status
        await _fetchTrialStatus();
      case Failure(:final failure):
        setState(() {
          _errorMessage = failure.message;
          _isActivating = false;
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    // Don't show card if loading or not eligible and no active trial
    if (_isLoading) {
      return const SizedBox.shrink();
    }

    if (!_isEligible && _daysRemaining == null) {
      return const SizedBox.shrink();
    }

    // If trial is active, show badge with days remaining
    if (_daysRemaining != null && _daysRemaining! > 0) {
      return Card(
        key: const Key('trial_card_active'),
        elevation: 2,
        color: CyberColors.matrixGreen.withAlpha(25),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Icon(
                Icons.card_giftcard,
                color: CyberColors.matrixGreen,
                size: 32,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.subscriptionTrialActive,
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: CyberColors.matrixGreen,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      l10n.subscriptionTrialDaysRemaining(_daysRemaining!),
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: CyberColors.matrixGreen,
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

    // If eligible, show "Start Trial" card
    if (_isEligible) {
      return Card(
        key: const Key('trial_card_eligible'),
        elevation: 2,
        color: colorScheme.primaryContainer,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.card_giftcard,
                    color: colorScheme.primary,
                    size: 32,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.subscriptionTrialTitle,
                          style: theme.textTheme.titleMedium?.copyWith(
                            color: colorScheme.primary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          l10n.subscriptionTrialDescription,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: colorScheme.onPrimaryContainer,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(
                  _errorMessage!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.error,
                  ),
                ),
              ],
              const SizedBox(height: 12),
              FilledButton(
                key: const Key('btn_start_trial'),
                onPressed: _isActivating ? null : _activateTrial,
                child: _isActivating
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l10n.subscriptionStartTrial),
              ),
            ],
          ),
        ),
      );
    }

    return const SizedBox.shrink();
  }
}
