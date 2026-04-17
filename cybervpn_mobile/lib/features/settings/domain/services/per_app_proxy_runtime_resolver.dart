import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/installed_app.dart';

/// Resolves settings-level per-app proxy preferences into Android blocked-apps.
class PerAppProxyRuntimeResolver {
  const PerAppProxyRuntimeResolver();

  List<String> resolveBlockedApps({
    required PerAppProxyMode mode,
    required Iterable<String> selectedAppIds,
    required Iterable<InstalledApp> installedApps,
    String? currentPackageName,
  }) {
    final availablePackages = installedApps
        .map((app) => app.packageName.trim())
        .where((packageName) => packageName.isNotEmpty)
        .where((packageName) => packageName != currentPackageName)
        .toSet();

    final selectedPackages = selectedAppIds
        .map((packageName) => packageName.trim())
        .where(availablePackages.contains)
        .toSet();

    final blockedApps = switch (mode) {
      PerAppProxyMode.off => const <String>{},
      PerAppProxyMode.bypassSelected => selectedPackages,
      PerAppProxyMode.proxySelected => availablePackages.difference(
        selectedPackages,
      ),
    };

    final result = blockedApps.toList()..sort();
    return result;
  }
}
