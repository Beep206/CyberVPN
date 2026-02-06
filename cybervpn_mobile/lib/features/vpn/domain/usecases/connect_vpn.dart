import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

@immutable
class ConnectVpnUseCase {
  final VpnRepository _repository;

  const ConnectVpnUseCase(this._repository);

  Future<Result<void>> call(VpnConfigEntity config) =>
      _repository.connect(config);
}
