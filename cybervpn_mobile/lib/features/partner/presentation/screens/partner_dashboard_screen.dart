import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/partner/presentation/providers/partner_provider.dart';
import 'package:cybervpn_mobile/features/partner/presentation/widgets/partner_stats_card.dart';
import 'package:cybervpn_mobile/features/partner/presentation/widgets/partner_code_card.dart';
import 'package:cybervpn_mobile/features/partner/presentation/widgets/earnings_list_item.dart';

// ---------------------------------------------------------------------------
// PartnerDashboardScreen
// ---------------------------------------------------------------------------

/// Partner dashboard with tabs for Dashboard, Codes, and Earnings.
///
/// For non-partners, shows a "Bind Code" input to become a partner.
/// For partners, shows full dashboard with statistics, codes, and earnings.
///
/// Supports pull-to-refresh and manual refresh via the AppBar action.
class PartnerDashboardScreen extends ConsumerStatefulWidget {
  const PartnerDashboardScreen({super.key});

  @override
  ConsumerState<PartnerDashboardScreen> createState() =>
      _PartnerDashboardScreenState();
}

class _PartnerDashboardScreenState
    extends ConsumerState<PartnerDashboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final asyncPartner = ref.watch(partnerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.partnerDashboardTitle),
        actions: [
          IconButton(
            key: const Key('btn_refresh_partner'),
            icon: const Icon(Icons.refresh),
            tooltip: l10n.commonRefresh,
            onPressed: () {
              unawaited(ref.read(partnerProvider.notifier).checkAvailability());
            },
          ),
        ],
        bottom: asyncPartner.when(
          data: (state) {
            if (state.isPartner) {
              return TabBar(
                controller: _tabController,
                tabs: [
                  Tab(
                    key: const Key('tab_dashboard'),
                    text: l10n.partnerDashboardTab,
                  ),
                  Tab(
                    key: const Key('tab_codes'),
                    text: l10n.partnerCodesTab,
                  ),
                  Tab(
                    key: const Key('tab_earnings'),
                    text: l10n.partnerEarningsTab,
                  ),
                ],
              );
            }
            return null;
          },
          loading: () => null,
          error: (error, stack) => null,
        ),
      ),
      body: asyncPartner.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorBody(
          message: error.toString(),
          onRetry: () => ref.invalidate(partnerProvider),
        ),
        data: (state) {
          if (!state.isAvailable) {
            return const _ComingSoonBody();
          }
          if (!state.isPartner) {
            return const _BindCodeBody();
          }
          return TabBarView(
            controller: _tabController,
            children: [
              _DashboardTab(state: state),
              _CodesTab(state: state),
              _EarningsTab(state: state),
            ],
          );
        },
      ),
      floatingActionButton: asyncPartner.when(
        data: (state) {
          // Show FAB only on Codes tab for partners
          if (state.isPartner && _tabController.index == 1) {
            return FloatingActionButton.extended(
              key: const Key('fab_create_code'),
              onPressed: () => _showCreateCodeDialog(context),
              icon: const Icon(Icons.add),
              label: Text(l10n.partnerCreateCode),
            );
          }
          return null;
        },
        loading: () => null,
        error: (_, _) => null,
      ),
    );
  }

  Future<void> _showCreateCodeDialog(BuildContext context) async {
    final l10n = AppLocalizations.of(context);
    final markupController = TextEditingController();
    final descriptionController = TextEditingController();

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.partnerCreateCode),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: markupController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: l10n.partnerMarkupPercentage,
                suffixText: '%',
              ),
            ),
            const SizedBox(height: Spacing.md),
            TextField(
              controller: descriptionController,
              decoration: InputDecoration(
                labelText: l10n.partnerCodeDescription,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () {
              final markup = double.tryParse(markupController.text);
              if (markup != null && markup >= 0 && markup <= 100) {
                Navigator.of(context).pop(true);
              }
            },
            child: Text(l10n.commonCreate),
          ),
        ],
      ),
    );

    if (result == true && context.mounted) {
      final markup = double.parse(markupController.text);
      final description = descriptionController.text.trim();

      final createResult = await ref.read(partnerProvider.notifier).createCode(
            markup: markup,
            description: description.isEmpty ? null : description,
          );

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              createResult is Success
                  ? l10n.partnerCodeCreated
                  : l10n.errorOccurred,
            ),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Dashboard Tab
// ---------------------------------------------------------------------------

class _DashboardTab extends StatelessWidget {
  const _DashboardTab({required this.state});

  final PartnerState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return ListView(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.md,
      ),
      children: [
        Text(
          l10n.partnerYourStats,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        if (state.partnerInfo != null)
          PartnerStatsCard(
            key: const Key('partner_stats'),
            info: state.partnerInfo!,
          ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.partnerRecentCodes,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        if (state.partnerCodes.isEmpty)
          _EmptyPlaceholder(message: l10n.partnerNoCodesYet)
        else
          ...state.partnerCodes.take(3).map(
                (code) => PartnerCodeCard(
                  key: ValueKey('code_${code.code}'),
                  code: code,
                ),
              ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Codes Tab
// ---------------------------------------------------------------------------

class _CodesTab extends StatelessWidget {
  const _CodesTab({required this.state});

  final PartnerState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return ListView(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.md,
      ),
      children: [
        if (state.partnerCodes.isEmpty)
          _EmptyPlaceholder(message: l10n.partnerNoCodesYet)
        else
          ...state.partnerCodes.map(
            (code) => PartnerCodeCard(
              key: ValueKey('code_${code.code}'),
              code: code,
            ),
          ),
        SizedBox(height: Spacing.navBarClearance(context) + 80),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Earnings Tab
// ---------------------------------------------------------------------------

class _EarningsTab extends StatelessWidget {
  const _EarningsTab({required this.state});

  final PartnerState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return ListView(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.md,
      ),
      children: [
        if (state.earnings.isEmpty)
          _EmptyPlaceholder(message: l10n.partnerNoEarningsYet)
        else
          ...state.earnings.map(
            (earning) => EarningsListItem(
              key: ValueKey('earning_${earning.period}_${earning.date}'),
              earnings: earning,
            ),
          ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Bind Code Body (for non-partners)
// ---------------------------------------------------------------------------

class _BindCodeBody extends ConsumerStatefulWidget {
  const _BindCodeBody();

  @override
  ConsumerState<_BindCodeBody> createState() => _BindCodeBodyState();
}

class _BindCodeBodyState extends ConsumerState<_BindCodeBody> {
  final _codeController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _onBind() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) return;

    setState(() => _isLoading = true);

    final result = await ref.read(partnerProvider.notifier).bindCode(code);

    if (mounted) {
      setState(() => _isLoading = false);

      final l10n = AppLocalizations.of(context);
      final message = switch (result) {
        Success(:final data) => data.message,
        Failure() => l10n.errorOccurred,
      };

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          duration: const Duration(seconds: 3),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(Spacing.xl),
              decoration: BoxDecoration(
                color: colorScheme.primary.withAlpha(20),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.handshake_outlined,
                size: 64,
                color: colorScheme.primary,
              ),
            ),
            const SizedBox(height: Spacing.lg),
            Text(
              l10n.partnerBecomePartnerTitle,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              l10n.partnerBecomePartnerDescription,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.xl),
            TextField(
              controller: _codeController,
              decoration: InputDecoration(
                labelText: l10n.partnerBindCodeLabel,
                hintText: l10n.partnerBindCodeHint,
                prefixIcon: const Icon(Icons.vpn_key_outlined),
              ),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _onBind(),
            ),
            const SizedBox(height: Spacing.md),
            FilledButton(
              onPressed: _isLoading ? null : _onBind,
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(l10n.partnerBindCode),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty Placeholder
// ---------------------------------------------------------------------------

class _EmptyPlaceholder extends StatelessWidget {
  const _EmptyPlaceholder({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: Spacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.inbox_outlined,
              size: 48,
              color: colorScheme.onSurfaceVariant.withAlpha(100),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              message,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Coming Soon Body
// ---------------------------------------------------------------------------

class _ComingSoonBody extends StatelessWidget {
  const _ComingSoonBody();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(Spacing.xl),
              decoration: BoxDecoration(
                color: colorScheme.primary.withAlpha(20),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.handshake_outlined,
                size: 64,
                color: colorScheme.primary,
              ),
            ),
            const SizedBox(height: Spacing.lg),
            Text(
              l10n.partnerComingSoonTitle,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              l10n.partnerComingSoonDescription,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
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
    final l10n = AppLocalizations.of(context);

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
                child: Text(l10n.retry),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
