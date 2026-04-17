import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/excluded_routes_screen.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

/// Routing screen for rule-based routing profiles and excluded routes.
class RoutingSettingsScreen extends ConsumerWidget {
  const RoutingSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSettings = ref.watch(settingsProvider);

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Failed to load routing settings')),
      data: (settings) => _RoutingSettingsContent(settings: settings),
    );

    if (embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Routing')),
      body: content,
    );
  }
}

class _RoutingSettingsContent extends ConsumerWidget {
  const _RoutingSettingsContent({required this.settings});

  final AppSettings settings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(settingsProvider.notifier);
    final supportMatrix = ref.watch(vpnSettingsSupportMatrixProvider);
    RoutingProfile? activeProfile;
    for (final profile in settings.routingProfiles) {
      if (profile.id == settings.activeRoutingProfileId) {
        activeProfile = profile;
        break;
      }
    }

    return ListView(
      children: [
        SettingsSection(
          title: 'Status',
          children: [
            SettingsTile.toggle(
              key: const Key('toggle_routing_enabled'),
              title: 'Enable routing rules',
              subtitle:
                  'Use named routing profiles to send traffic through Proxy, Direct, or Block actions.',
              value: settings.routingEnabled,
              onChanged: (_) =>
                  notifier.updateRoutingEnabled(!settings.routingEnabled),
            ),
            SettingsTile.info(
              key: const Key('routing_active_profile_tile'),
              title: 'Active profile',
              subtitle: activeProfile == null
                  ? 'No active profile selected.'
                  : '${activeProfile.name} • ${activeProfile.rules.where((rule) => rule.enabled).length} enabled rule(s)',
            ),
          ],
        ),
        if (supportMatrix.excludedRoutes.isVisible)
          SettingsSection(
            title: 'Tunnel bypass',
            children: [
              SettingsTile.navigation(
                key: const Key('nav_routing_excluded_routes'),
                title: 'Excluded Routes',
                subtitle: settings.bypassSubnets.isEmpty
                    ? 'No excluded routes configured'
                    : '${settings.bypassSubnets.length} route(s) configured',
                leading: const Icon(Icons.alt_route_outlined),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const ExcludedRoutesScreen(),
                  ),
                ),
              ),
            ],
          ),
        if (!supportMatrix.excludedRoutes.isVisible)
          _CapabilityNotice(
            key: const Key('routing_excluded_routes_notice'),
            message:
                supportMatrix.excludedRoutes.message ??
                'Excluded Routes are unavailable on this platform.',
          ),
        SettingsSection(
          title: 'Profiles',
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                Spacing.md,
                Spacing.sm,
                Spacing.md,
                Spacing.sm,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      settings.routingProfiles.isEmpty
                          ? 'No routing profiles created yet.'
                          : '${settings.routingProfiles.length} profile(s) available.',
                    ),
                  ),
                  FilledButton.tonalIcon(
                    key: const Key('button_add_routing_profile'),
                    onPressed: () => _showProfileEditorDialog(context, ref),
                    icon: const Icon(Icons.add),
                    label: const Text('Add profile'),
                  ),
                ],
              ),
            ),
            if (settings.routingProfiles.isEmpty)
              const ListTile(
                title: Text('Create a routing profile'),
                subtitle: Text(
                  'Profiles group routing rules so you can enable them on demand and keep one active configuration.',
                ),
              )
            else
              for (final profile in settings.routingProfiles)
                _RoutingProfileCard(
                  profile: profile,
                  isActive: profile.id == settings.activeRoutingProfileId,
                  onActivate: () =>
                      notifier.setActiveRoutingProfile(profile.id),
                  onEdit: () => _showProfileEditorDialog(
                    context,
                    ref,
                    initialProfile: profile,
                  ),
                  onDelete: () => _confirmDeleteProfile(context, ref, profile),
                ),
          ],
        ),
        const _CapabilityNotice(
          message:
              'Routing profiles are stored in app settings and applied on the next VPN connection through the runtime config builder.',
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }

  Future<void> _confirmDeleteProfile(
    BuildContext context,
    WidgetRef ref,
    RoutingProfile profile,
  ) async {
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete routing profile'),
        content: Text('Delete "${profile.name}" and all of its rules?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (shouldDelete == true) {
      await ref
          .read(settingsProvider.notifier)
          .removeRoutingProfile(profile.id);
    }
  }

  Future<void> _showProfileEditorDialog(
    BuildContext context,
    WidgetRef ref, {
    RoutingProfile? initialProfile,
  }) async {
    final profileNameController = TextEditingController(
      text: initialProfile?.name ?? '',
    );
    final descriptionController = TextEditingController(
      text: initialProfile?.description ?? '',
    );
    final editableRules =
        initialProfile?.rules
            .map(_EditableRoutingRule.fromRoutingRule)
            .toList() ??
        <_EditableRoutingRule>[
          _EditableRoutingRule(
            id: _newId(),
            matchType: RoutingRuleMatchType.domainSuffix,
            value: '',
            action: RoutingRuleAction.proxy,
            enabled: true,
          ),
        ];

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: Text(
                initialProfile == null
                    ? 'Create routing profile'
                    : 'Edit routing profile',
              ),
              content: SizedBox(
                width: 560,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        key: const Key('input_routing_profile_name'),
                        controller: profileNameController,
                        decoration: const InputDecoration(
                          labelText: 'Profile name',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: Spacing.sm),
                      TextField(
                        key: const Key('input_routing_profile_description'),
                        controller: descriptionController,
                        decoration: const InputDecoration(
                          labelText: 'Description',
                          border: OutlineInputBorder(),
                        ),
                        maxLines: 2,
                      ),
                      const SizedBox(height: Spacing.md),
                      Row(
                        children: [
                          Text(
                            'Rules',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const Spacer(),
                          TextButton.icon(
                            key: const Key('button_add_routing_rule'),
                            onPressed: () {
                              setState(() {
                                editableRules.add(
                                  _EditableRoutingRule(
                                    id: _newId(),
                                    matchType:
                                        RoutingRuleMatchType.domainSuffix,
                                    value: '',
                                    action: RoutingRuleAction.proxy,
                                    enabled: true,
                                  ),
                                );
                              });
                            },
                            icon: const Icon(Icons.add),
                            label: const Text('Add rule'),
                          ),
                        ],
                      ),
                      const SizedBox(height: Spacing.sm),
                      for (var index = 0; index < editableRules.length; index++)
                        _RoutingRuleEditor(
                          rule: editableRules[index],
                          index: index,
                          onChanged: (rule) {
                            setState(() => editableRules[index] = rule);
                          },
                          onRemove: editableRules.length == 1
                              ? null
                              : () {
                                  setState(() => editableRules.removeAt(index));
                                },
                        ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  key: const Key('button_save_routing_profile'),
                  onPressed: () async {
                    final name = profileNameController.text.trim();
                    final rules = editableRules
                        .map((rule) => rule.toRoutingRule())
                        .where((rule) => rule.value.trim().isNotEmpty)
                        .toList();

                    if (name.isEmpty || rules.isEmpty) {
                      return;
                    }

                    final profile = RoutingProfile(
                      id: initialProfile?.id ?? _newId(),
                      name: name,
                      description: descriptionController.text.trim().isEmpty
                          ? null
                          : descriptionController.text.trim(),
                      enabled: true,
                      rules: rules,
                    );

                    await ref
                        .read(settingsProvider.notifier)
                        .upsertRoutingProfile(profile);

                    final settings = await ref.read(settingsProvider.future);
                    if (settings.activeRoutingProfileId == null) {
                      await ref
                          .read(settingsProvider.notifier)
                          .setActiveRoutingProfile(profile.id);
                    }

                    if (dialogContext.mounted) {
                      Navigator.of(dialogContext).pop();
                    }
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  static String _newId() {
    return DateTime.now().microsecondsSinceEpoch.toString();
  }
}

class _RoutingProfileCard extends StatelessWidget {
  const _RoutingProfileCard({
    required this.profile,
    required this.isActive,
    required this.onActivate,
    required this.onEdit,
    required this.onDelete,
  });

  final RoutingProfile profile;
  final bool isActive;
  final VoidCallback onActivate;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final enabledRules = profile.rules.where((rule) => rule.enabled).length;

    return Card(
      margin: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.xs,
        Spacing.md,
        Spacing.sm,
      ),
      child: Column(
        children: [
          ListTile(
            key: Key('routing_profile_${profile.id}'),
            title: Text(profile.name),
            subtitle: Text(
              profile.description?.isNotEmpty == true
                  ? '${profile.description} • $enabledRules enabled rule(s)'
                  : '$enabledRules enabled rule(s)',
            ),
            leading: Icon(
              isActive
                  ? Icons.radio_button_checked
                  : Icons.radio_button_unchecked,
            ),
            trailing: Wrap(
              spacing: 4,
              children: [
                IconButton(
                  key: Key('button_edit_routing_profile_${profile.id}'),
                  tooltip: 'Edit profile',
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined),
                ),
                IconButton(
                  key: Key('button_delete_routing_profile_${profile.id}'),
                  tooltip: 'Delete profile',
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            onTap: onActivate,
          ),
          if (profile.rules.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                Spacing.md,
                0,
                Spacing.md,
                Spacing.md,
              ),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final rule in profile.rules.take(3))
                    Chip(
                      label: Text(
                        '${rule.matchType.name}:${rule.value} → ${rule.action.name}',
                      ),
                    ),
                  if (profile.rules.length > 3)
                    Chip(label: Text('+${profile.rules.length - 3} more')),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _RoutingRuleEditor extends StatelessWidget {
  const _RoutingRuleEditor({
    required this.rule,
    required this.index,
    required this.onChanged,
    this.onRemove,
  });

  final _EditableRoutingRule rule;
  final int index;
  final ValueChanged<_EditableRoutingRule> onChanged;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.md),
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(Radii.md),
          border: Border.all(color: Theme.of(context).dividerColor),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            children: [
              Row(
                children: [
                  Text('Rule ${index + 1}'),
                  const Spacer(),
                  if (onRemove != null)
                    IconButton(
                      onPressed: onRemove,
                      icon: const Icon(Icons.remove_circle_outline),
                    ),
                ],
              ),
              const SizedBox(height: Spacing.sm),
              DropdownButtonFormField<RoutingRuleMatchType>(
                key: Key('dropdown_match_type_$index'),
                initialValue: rule.matchType,
                decoration: const InputDecoration(
                  labelText: 'Match type',
                  border: OutlineInputBorder(),
                ),
                items: RoutingRuleMatchType.values
                    .map(
                      (matchType) => DropdownMenuItem(
                        value: matchType,
                        child: Text(matchType.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value == null) return;
                  onChanged(rule.copyWith(matchType: value));
                },
              ),
              const SizedBox(height: Spacing.sm),
              TextFormField(
                key: Key('input_routing_rule_value_$index'),
                initialValue: rule.value,
                decoration: const InputDecoration(
                  labelText: 'Value',
                  border: OutlineInputBorder(),
                ),
                onChanged: (value) => onChanged(rule.copyWith(value: value)),
              ),
              const SizedBox(height: Spacing.sm),
              DropdownButtonFormField<RoutingRuleAction>(
                key: Key('dropdown_rule_action_$index'),
                initialValue: rule.action,
                decoration: const InputDecoration(
                  labelText: 'Action',
                  border: OutlineInputBorder(),
                ),
                items: RoutingRuleAction.values
                    .map(
                      (action) => DropdownMenuItem(
                        value: action,
                        child: Text(action.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value == null) return;
                  onChanged(rule.copyWith(action: value));
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EditableRoutingRule {
  const _EditableRoutingRule({
    required this.id,
    required this.matchType,
    required this.value,
    required this.action,
    required this.enabled,
  });

  factory _EditableRoutingRule.fromRoutingRule(RoutingRule rule) {
    return _EditableRoutingRule(
      id: rule.id,
      matchType: rule.matchType,
      value: rule.value,
      action: rule.action,
      enabled: rule.enabled,
    );
  }

  final String id;
  final RoutingRuleMatchType matchType;
  final String value;
  final RoutingRuleAction action;
  final bool enabled;

  _EditableRoutingRule copyWith({
    String? id,
    RoutingRuleMatchType? matchType,
    String? value,
    RoutingRuleAction? action,
    bool? enabled,
  }) {
    return _EditableRoutingRule(
      id: id ?? this.id,
      matchType: matchType ?? this.matchType,
      value: value ?? this.value,
      action: action ?? this.action,
      enabled: enabled ?? this.enabled,
    );
  }

  RoutingRule toRoutingRule() {
    return RoutingRule(
      id: id,
      matchType: matchType,
      value: value.trim(),
      action: action,
      enabled: enabled,
    );
  }
}

class _CapabilityNotice extends StatelessWidget {
  const _CapabilityNotice({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.sm,
        Spacing.md,
        Spacing.md,
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(Radii.lg),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Text(message),
        ),
      ),
    );
  }
}
