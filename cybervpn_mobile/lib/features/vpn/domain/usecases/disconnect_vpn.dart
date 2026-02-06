import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

@immutable
class DisconnectVpnUseCase {
  final VpnRepository _repository;

  const DisconnectVpnUseCase(this._repository);

  Future<void> call() async {
    final result = await _repository.disconnect();
    switch (result) {
      case Success():
        return;
      case Failure(:final failure):
        throw failure;
    }
  }
}
