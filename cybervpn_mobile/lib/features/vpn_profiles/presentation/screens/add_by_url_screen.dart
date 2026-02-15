import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_card.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

/// Screen for adding a VPN profile by entering a subscription URL.
///
/// Features:
/// - URL text field with paste button
/// - Optional profile name field
/// - Fetch button with loading state
/// - Success state showing server count
/// - Error state with retry
/// - Save button to persist the profile
class AddByUrlScreen extends ConsumerStatefulWidget {
  const AddByUrlScreen({super.key});

  @override
  ConsumerState<AddByUrlScreen> createState() => _AddByUrlScreenState();
}

class _AddByUrlScreenState extends ConsumerState<AddByUrlScreen> {
  late final TextEditingController _urlController;
  late final TextEditingController _nameController;
  final _formKey = GlobalKey<FormState>();

  _FetchState _fetchState = _FetchState.idle;
  int _fetchedServerCount = 0;
  String? _fetchError;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController();
    _nameController = TextEditingController();
  }

  @override
  void dispose() {
    _urlController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  Future<void> _pasteFromClipboard() async {
    try {
      final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
      final text = clipboardData?.text?.trim();
      if (text != null && text.isNotEmpty) {
        setState(() {
          _urlController.text = text;
        });
      }
    } catch (_) {
      // Clipboard access may fail on some platforms
    }
  }

  Future<void> _fetchSubscription() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _fetchState = _FetchState.loading;
      _fetchError = null;
    });

    // TODO(ui-5): Replace mock fetch with actual SubscriptionFetcher
    await Future<void>.delayed(const Duration(seconds: 2));

    if (!mounted) return;

    // Mock success — replace with real fetch result
    setState(() {
      _fetchState = _FetchState.success;
      _fetchedServerCount = 12;
    });
  }

  Future<void> _saveProfile() async {
    // TODO(ui-5): Save profile via notifier
    if (!mounted) return;

    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(l10n.profileSaved),
        behavior: SnackBarBehavior.floating,
      ),
    );
    Navigator.of(context).pop();
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: l10n.addProfileByUrl,
          style: theme.appBarTheme.titleTextStyle,
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.md,
          vertical: Spacing.md,
        ),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // --- URL input ---
              CyberCard(
                color: CyberColors.neonCyan,
                isAnimated: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.addProfileByUrl,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontFamily: 'Orbitron',
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: Spacing.sm),
                    TextFormField(
                      controller: _urlController,
                      decoration: InputDecoration(
                        hintText: l10n.profileUrlHint,
                        prefixIcon: const Icon(Icons.link, size: 20),
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.content_paste, size: 20),
                          tooltip: l10n.addProfileByClipboard,
                          onPressed: _pasteFromClipboard,
                        ),
                        isDense: true,
                      ),
                      keyboardType: TextInputType.url,
                      textInputAction: TextInputAction.next,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return l10n.profileUrlHint;
                        }
                        final uri = Uri.tryParse(value.trim());
                        if (uri == null || !uri.hasScheme) {
                          return l10n.profileUrlHint;
                        }
                        return null;
                      },
                    ),
                  ],
                ),
              ),

              const SizedBox(height: Spacing.md),

              // --- Optional name ---
              CyberCard(
                color: CyberColors.neonCyan,
                isAnimated: false,
                child: TextFormField(
                  controller: _nameController,
                  decoration: InputDecoration(
                    hintText: l10n.profileNameHint,
                    prefixIcon: const Icon(Icons.label_outline, size: 20),
                    isDense: true,
                  ),
                  textInputAction: TextInputAction.done,
                ),
              ),

              const SizedBox(height: Spacing.lg),

              // --- Fetch button ---
              if (_fetchState != _FetchState.success)
                FilledButton.icon(
                  onPressed: _fetchState == _FetchState.loading
                      ? null
                      : _fetchSubscription,
                  icon: _fetchState == _FetchState.loading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            value: null,
                          ),
                        )
                      : const Icon(Icons.download),
                  label: Text(
                    _fetchState == _FetchState.loading
                        ? l10n.connecting
                        : l10n.profileUpdateNow,
                  ),
                ),

              // --- Error state ---
              if (_fetchState == _FetchState.error && _fetchError != null) ...[
                const SizedBox(height: Spacing.sm),
                CyberCard(
                  color: CyberColors.neonPink,
                  isAnimated: false,
                  child: Row(
                    children: [
                      const Icon(
                        Icons.error_outline,
                        color: CyberColors.neonPink,
                        size: 20,
                      ),
                      const SizedBox(width: Spacing.sm),
                      Expanded(
                        child: Text(
                          l10n.profileFetchError(_fetchError!),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: CyberColors.neonPink,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // --- Success state ---
              if (_fetchState == _FetchState.success) ...[
                CyberCard(
                  color: CyberColors.matrixGreen,
                  child: Column(
                    children: [
                      const Icon(
                        Icons.check_circle,
                        color: CyberColors.matrixGreen,
                        size: 48,
                      ),
                      const SizedBox(height: Spacing.sm),
                      Text(
                        l10n.profileFetchSuccess(_fetchedServerCount),
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontFamily: 'Orbitron',
                          color: CyberColors.matrixGreen,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.lg),

                // --- Save button ---
                FilledButton.icon(
                  onPressed: _saveProfile,
                  icon: const Icon(Icons.save),
                  label: Text(l10n.commonSave),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ],

              SizedBox(height: Spacing.navBarClearance(context)),
            ],
          ),
        ),
      ),
    );
  }
}

enum _FetchState { idle, loading, success, error }
