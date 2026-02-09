import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';

/// Response from OAuth authorize endpoint.
class OAuthAuthorizeResponse {
  final String authorizeUrl;
  final String state;

  OAuthAuthorizeResponse({
    required this.authorizeUrl,
    required this.state,
  });

  factory OAuthAuthorizeResponse.fromJson(Map<String, dynamic> json) {
    return OAuthAuthorizeResponse(
      authorizeUrl: json['authorize_url'] as String,
      state: json['state'] as String,
    );
  }
}

/// Response from OAuth login callback.
class OAuthLoginResponse {
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
  final UserModel user;
  final bool isNewUser;
  final bool requires2fa;
  final String? tfaToken;

  OAuthLoginResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
    required this.user,
    required this.isNewUser,
    required this.requires2fa,
    this.tfaToken,
  });

  factory OAuthLoginResponse.fromJson(Map<String, dynamic> json) {
    return OAuthLoginResponse(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      tokenType: json['token_type'] as String,
      expiresIn: json['expires_in'] as int,
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
      isNewUser: json['is_new_user'] as bool? ?? false,
      requires2fa: json['requires_2fa'] as bool? ?? false,
      tfaToken: json['tfa_token'] as String?,
    );
  }

  TokenModel toTokenModel() => TokenModel(
        accessToken: accessToken,
        refreshToken: refreshToken,
        tokenType: tokenType,
        expiresIn: expiresIn,
      );
}

/// Data source for OAuth login API calls.
abstract class OAuthRemoteDataSource {
  /// Get the OAuth authorization URL for a provider.
  Future<OAuthAuthorizeResponse> getAuthorizeUrl({
    required String provider,
    required String redirectUri,
  });

  /// Complete the OAuth login callback.
  Future<OAuthLoginResponse> loginCallback({
    required String provider,
    required String code,
    required String state,
    required String redirectUri,
  });
}

class OAuthRemoteDataSourceImpl implements OAuthRemoteDataSource {
  final ApiClient _apiClient;

  OAuthRemoteDataSourceImpl(this._apiClient);

  @override
  Future<OAuthAuthorizeResponse> getAuthorizeUrl({
    required String provider,
    required String redirectUri,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/api/v1/oauth/$provider/login',
      queryParameters: {'redirect_uri': redirectUri},
    );
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw FormatException('Expected Map response, got ${data.runtimeType}');
    }
    return OAuthAuthorizeResponse.fromJson(data);
  }

  @override
  Future<OAuthLoginResponse> loginCallback({
    required String provider,
    required String code,
    required String state,
    required String redirectUri,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/api/v1/oauth/$provider/login/callback',
      data: {
        'code': code,
        'state': state,
        'redirect_uri': redirectUri,
      },
    );
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw FormatException('Expected Map response, got ${data.runtimeType}');
    }
    return OAuthLoginResponse.fromJson(data);
  }
}
