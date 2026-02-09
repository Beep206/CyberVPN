import 'package:connectivity_plus/connectivity_plus.dart';

class NetworkInfo {
  final Connectivity _connectivity;

  NetworkInfo({Connectivity? connectivity}) : _connectivity = connectivity ?? Connectivity();

  Future<bool> get isConnected async {
    try {
      final result = await _connectivity
          .checkConnectivity()
          .timeout(const Duration(seconds: 2));
      return !result.contains(ConnectivityResult.none);
    } catch (_) {
      // Assume connected on timeout; let HTTP calls determine reality.
      return true;
    }
  }

  Stream<bool> get onConnectivityChanged {
    return _connectivity.onConnectivityChanged.map(
      (results) => !results.contains(ConnectivityResult.none),
    );
  }
}
