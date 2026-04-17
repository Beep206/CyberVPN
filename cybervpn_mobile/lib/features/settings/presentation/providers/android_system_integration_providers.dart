import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/settings/data/datasources/android_system_integration_service.dart';

final androidSystemIntegrationServiceProvider =
    Provider<AndroidSystemIntegrationService>((ref) {
      return MethodChannelAndroidSystemIntegrationService();
    });

final lanProxyStatusProvider =
    FutureProvider.autoDispose.family<LanProxyStatus, bool>((ref, enabled) {
      return ref
          .watch(androidSystemIntegrationServiceProvider)
          .readLanProxyStatus(enabled: enabled);
    });

final appAutoStartStatusProvider =
    FutureProvider.autoDispose.family<AppAutoStartStatus, bool>((ref, enabled) {
      return ref
          .watch(androidSystemIntegrationServiceProvider)
          .readAppAutoStartStatus(enabled: enabled);
    });
