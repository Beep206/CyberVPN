import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/settings/data/datasources/per_app_proxy_platform_service.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/installed_app.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/per_app_proxy_runtime_resolver.dart';

final perAppProxyPlatformServiceProvider = Provider<PerAppProxyPlatformService>(
  (ref) => const MethodChannelPerAppProxyPlatformService(),
);

final perAppProxyRuntimeResolverProvider = Provider<PerAppProxyRuntimeResolver>(
  (ref) => const PerAppProxyRuntimeResolver(),
);

final installedAppsProvider = FutureProvider<List<InstalledApp>>((ref) async {
  final service = ref.watch(perAppProxyPlatformServiceProvider);
  return service.getInstalledApps();
});

final currentPackageNameProvider = FutureProvider<String?>((ref) async {
  final service = ref.watch(perAppProxyPlatformServiceProvider);
  return service.getCurrentPackageName();
});
