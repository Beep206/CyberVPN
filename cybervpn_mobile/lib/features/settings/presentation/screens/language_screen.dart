import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/language_repository.dart';
import 'package:cybervpn_mobile/features/settings/domain/models/language_item.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// LanguageScreen
// ---------------------------------------------------------------------------

/// Searchable language picker screen.
///
/// Displays a list of supported locales with flag emojis, native names,
/// and English names. The currently selected language shows a checkmark.
/// A search field at the top filters by native or English name.
class LanguageScreen extends ConsumerStatefulWidget {
  const LanguageScreen({super.key});

  @override
  ConsumerState<LanguageScreen> createState() => _LanguageScreenState();
}

class _LanguageScreenState extends ConsumerState<LanguageScreen> {
  final _searchController = TextEditingController();
  final _languageRepository = const LanguageRepository();

  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  // -- Filtering --------------------------------------------------------------

  /// Returns the list of languages matching the current search query.
  ///
  /// Matches against both [LanguageItem.nativeName] and
  /// [LanguageItem.englishName], case-insensitive.
  List<LanguageItem> _filteredLanguages() {
    final all = _languageRepository.getAvailableLanguages();
    if (_searchQuery.isEmpty) return all;

    final query = _searchQuery.toLowerCase();
    return all.where((lang) {
      return lang.nativeName.toLowerCase().contains(query) ||
          lang.englishName.toLowerCase().contains(query);
    }).toList();
  }

  // -- Build ------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final currentLocale = ref.watch(currentLocaleProvider);
    final filtered = _filteredLanguages();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Language'),
      ),
      body: Column(
        children: [
          // Search field
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: TextField(
              key: const Key('language_search_field'),
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search language...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        key: const Key('language_search_clear'),
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.md),
                ),
              ),
              onChanged: (value) => setState(() => _searchQuery = value),
            ),
          ),

          // Language list
          Expanded(
            child: filtered.isEmpty
                ? _buildEmptyState(context)
                : ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (context, index) {
                      final lang = filtered[index];
                      final isSelected = lang.localeCode == currentLocale;
                      return _LanguageTile(
                        key: Key('language_tile_${lang.localeCode}'),
                        language: lang,
                        isSelected: isSelected,
                        onTap: () => _onLanguageSelected(lang),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  // -- Empty state ------------------------------------------------------------

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.search_off,
            size: 48,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: Spacing.sm),
          Text(
            'No languages found',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  // -- Selection callback -----------------------------------------------------

  Future<void> _onLanguageSelected(LanguageItem language) async {
    final notifier = ref.read(settingsProvider.notifier);
    await notifier.updateLocale(language.localeCode);

    if (mounted) {
      Navigator.of(context).pop();
    }
  }
}

// ---------------------------------------------------------------------------
// _LanguageTile
// ---------------------------------------------------------------------------

/// A single language row in the picker list.
class _LanguageTile extends StatelessWidget {
  const _LanguageTile({
    super.key,
    required this.language,
    required this.isSelected,
    required this.onTap,
  });

  final LanguageItem language;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ListTile(
      leading: Text(
        language.flagEmoji,
        style: const TextStyle(fontSize: 24),
      ),
      title: Text(
        language.nativeName,
        style: theme.textTheme.bodyLarge?.copyWith(
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
          color: theme.colorScheme.onSurface,
        ),
      ),
      subtitle: Text(
        language.englishName,
        style: theme.textTheme.bodySmall?.copyWith(
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
      trailing: isSelected
          ? Icon(
              Icons.check,
              color: theme.colorScheme.primary,
            )
          : null,
      onTap: onTap,
    );
  }
}
