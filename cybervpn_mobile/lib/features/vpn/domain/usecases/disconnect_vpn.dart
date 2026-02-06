import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

@immutable
class DisconnectVpnUseCase {
  final VpnRepository _repository;

  const DisconnectVpnUseCase(this._repository);

  Future<Result<void>> call() => _repository.disconnect();
}
