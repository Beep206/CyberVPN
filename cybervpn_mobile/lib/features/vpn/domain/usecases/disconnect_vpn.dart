import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

class DisconnectVpnUseCase {
  final VpnRepository _repository;

  const DisconnectVpnUseCase(this._repository);

  Future<void> call() async {
    await _repository.disconnect();
  }
}
