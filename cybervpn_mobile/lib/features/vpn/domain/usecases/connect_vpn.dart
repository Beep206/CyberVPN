import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

class ConnectVpnUseCase {
  final VpnRepository _repository;

  const ConnectVpnUseCase(this._repository);

  Future<void> call(VpnConfigEntity config) async {
    final result = await _repository.connect(config);
    switch (result) {
      case Success():
        return;
      case Failure(:final failure):
        throw failure;
    }
  }
}
