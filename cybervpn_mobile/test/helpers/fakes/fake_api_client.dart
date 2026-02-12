import 'package:dio/dio.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';

/// A fake [ApiClient] for testing that returns configurable responses.
///
/// Usage:
/// ```dart
/// final fakeApi = FakeApiClient();
/// fakeApi.setGetResponse('/users/me', {'id': 'user-001', 'email': 'test@example.com'});
/// ```
class FakeApiClient extends ApiClient {
  FakeApiClient() : super(baseUrl: 'http://localhost');

  final Map<String, _FakeResponse> _getResponses = {};
  final Map<String, _FakeResponse> _postResponses = {};
  final Map<String, _FakeResponse> _patchResponses = {};
  final Map<String, _FakeResponse> _deleteResponses = {};

  /// Configures a GET response for the given [path].
  void setGetResponse(String path, dynamic data, {int statusCode = 200}) {
    _getResponses[path] = _FakeResponse(data: data, statusCode: statusCode);
  }

  /// Configures a POST response for the given [path].
  void setPostResponse(String path, dynamic data, {int statusCode = 200}) {
    _postResponses[path] = _FakeResponse(data: data, statusCode: statusCode);
  }

  /// Configures a PATCH response for the given [path].
  void setPatchResponse(String path, dynamic data, {int statusCode = 200}) {
    _patchResponses[path] = _FakeResponse(data: data, statusCode: statusCode);
  }

  /// Configures a DELETE response for the given [path].
  void setDeleteResponse(String path, dynamic data, {int statusCode = 200}) {
    _deleteResponses[path] = _FakeResponse(data: data, statusCode: statusCode);
  }

  /// Configures an error response for GET on the given [path].
  void setGetError(String path, Exception error) {
    _getResponses[path] = _FakeResponse(error: error);
  }

  /// Configures an error response for POST on the given [path].
  void setPostError(String path, Exception error) {
    _postResponses[path] = _FakeResponse(error: error);
  }

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _resolve<T>(_getResponses, path);
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _resolve<T>(_postResponses, path);
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _resolve<T>(_patchResponses, path);
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return _resolve<T>(_deleteResponses, path);
  }

  Future<Response<T>> _resolve<T>(
    Map<String, _FakeResponse> responses,
    String path,
  ) async {
    final fakeResponse = responses[path];
    if (fakeResponse == null) {
      throw StateError('No fake response configured for path: $path');
    }
    if (fakeResponse.error != null) {
      throw fakeResponse.error!;
    }
    return Response<T>(
      data: fakeResponse.data as T,
      statusCode: fakeResponse.statusCode,
      requestOptions: RequestOptions(path: path),
    );
  }

  /// Clears all configured responses.
  void reset() {
    _getResponses.clear();
    _postResponses.clear();
    _patchResponses.clear();
    _deleteResponses.clear();
  }
}

class _FakeResponse {
  _FakeResponse({this.data, this.statusCode = 200, this.error});

  final dynamic data;
  final int statusCode;
  final Exception? error;
}
