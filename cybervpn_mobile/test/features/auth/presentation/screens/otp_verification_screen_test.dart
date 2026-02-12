import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/screens/otp_verification_screen.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockApiClient extends Mock implements ApiClient {}

class MockSecureStorage extends Mock implements SecureStorage {}

class MockAuthNotifier extends Mock implements AuthNotifier {}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

void ignoreOverflowErrors(
  FlutterErrorDetails details, {
  bool forceReport = false,
}) {
  bool ifIsOverflowError = false;
  bool isUnableToLoadAsset = false;

  // Ignore overflow errors
  final exception = details.exception;
  if (exception is FlutterError) {
    ifIsOverflowError = !exception.diagnostics.any(
      (e) => e.value.toString().startsWith('A RenderFlex overflowed by'),
    );
    isUnableToLoadAsset = !exception.diagnostics.any(
      (e) => e.value.toString().startsWith('Unable to load asset'),
    );
  }

  if (ifIsOverflowError || isUnableToLoadAsset) {
    debugPrint('Ignoring error: ${details.exception}');
  } else {
    FlutterError.dumpErrorToConsole(details, forceReport: forceReport);
  }
}

Widget buildTestableOtpScreen({
  required String email,
  required MockApiClient mockApiClient,
  required MockSecureStorage mockSecureStorage,
  required MockAuthNotifier mockAuthNotifier,
}) {
  return ProviderScope(
    overrides: [
      apiClientProvider.overrideWithValue(mockApiClient),
      secureStorageProvider.overrideWithValue(mockSecureStorage),
      authProvider.overrideWith((ref) => mockAuthNotifier),
    ],
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: OtpVerificationScreen(email: email),
    ),
  );
}

// Finders
Finder findCodeField() => find.byType(TextFormField);
Finder findSubmitButton() => find.widgetWithText(FilledButton, 'Verify Code');
Finder findResendButton() => find.widgetWithText(TextButton, 'Resend Code');
Finder findBackToLoginButton() => find.widgetWithText(TextButton, 'Back to Login');
Finder findErrorIcon() => find.byIcon(Icons.error_outline);
Finder findSuccessIcon() => find.byIcon(Icons.check_circle_outline);
Finder findRateLimitIcon() => find.byIcon(Icons.hourglass_top);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockApiClient mockApiClient;
  late MockSecureStorage mockSecureStorage;
  late MockAuthNotifier mockAuthNotifier;

  setUp(() {
    mockApiClient = MockApiClient();
    mockSecureStorage = MockSecureStorage();
    mockAuthNotifier = MockAuthNotifier();

    FlutterError.onError = ignoreOverflowErrors;
  });

  group('OtpVerificationScreen - Rendering', () {
    testWidgets('test_renders_otp_form_elements', (tester) async {
      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      expect(find.text('Verify Email'), findsOneWidget);
      expect(find.text('test@example.com'), findsOneWidget);
      expect(findCodeField(), findsOneWidget);
      expect(findSubmitButton(), findsOneWidget);
      expect(findResendButton(), findsOneWidget);
      expect(findBackToLoginButton(), findsOneWidget);
    });

    testWidgets('test_renders_email_icon', (tester) async {
      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'user@test.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      expect(find.byIcon(Icons.mark_email_unread_outlined), findsOneWidget);
    });
  });

  group('OtpVerificationScreen - Form Validation', () {
    testWidgets('test_validates_empty_code', (tester) async {
      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(find.text('This field is required'), findsOneWidget);
    });

    testWidgets('test_validates_code_length_less_than_6', (tester) async {
      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '12345');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(find.text('Invalid verification code'), findsOneWidget);
    });

    testWidgets('test_accepts_valid_6_digit_code', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {
            'access_token': 'valid_access_token',
            'refresh_token': 'valid_refresh_token',
          },
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.verifyEmail),
        ),
      );

      when(() => mockSecureStorage.setTokens(
            accessToken: any(named: 'accessToken'),
            refreshToken: any(named: 'refreshToken'),
          )).thenAnswer((_) async => {});

      when(() => mockAuthNotifier.checkAuthStatus())
          .thenAnswer((_) async => {});

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '123456');
      await tester.tap(findSubmitButton());
      await tester.pump();

      // Should show loading state
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('OtpVerificationScreen - Successful Verification', () {
    testWidgets('test_successful_verification_stores_tokens', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {
            'access_token': 'new_access',
            'refresh_token': 'new_refresh',
          },
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.verifyEmail),
        ),
      );

      when(() => mockSecureStorage.setTokens(
            accessToken: 'new_access',
            refreshToken: 'new_refresh',
          )).thenAnswer((_) async => {});

      when(() => mockAuthNotifier.checkAuthStatus())
          .thenAnswer((_) async => {});

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '123456');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      verify(() => mockSecureStorage.setTokens(
            accessToken: 'new_access',
            refreshToken: 'new_refresh',
          )).called(1);
      verify(() => mockAuthNotifier.checkAuthStatus()).called(1);
    });

    testWidgets('test_successful_verification_shows_success_state',
        (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {
            'access_token': 'token',
            'refresh_token': 'refresh',
          },
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.verifyEmail),
        ),
      );

      when(() => mockSecureStorage.setTokens(
            accessToken: any(named: 'accessToken'),
            refreshToken: any(named: 'refreshToken'),
          )).thenAnswer((_) async => {});

      when(() => mockAuthNotifier.checkAuthStatus())
          .thenAnswer((_) async => {});

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '123456');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findSuccessIcon(), findsOneWidget);
      expect(find.text('Email Verified'), findsOneWidget);
    });
  });

  group('OtpVerificationScreen - Error Handling', () {
    testWidgets('test_invalid_code_shows_error', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(message: 'Invalid verification code', code: 400),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '999999');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findErrorIcon(), findsOneWidget);
      expect(find.text('Invalid verification code'), findsOneWidget);
    });

    testWidgets('test_expired_code_shows_error', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(message: 'Code expired', code: 422),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '000000');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findErrorIcon(), findsOneWidget);
      expect(find.text('Invalid verification code'), findsOneWidget);
    });

    testWidgets('test_network_error_shows_message', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenThrow(
        const NetworkException(message: 'No internet connection'),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '123456');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findErrorIcon(), findsOneWidget);
      expect(find.text('No internet connection'), findsOneWidget);
    });
  });

  group('OtpVerificationScreen - Rate Limiting', () {
    testWidgets('test_rate_limit_429_shows_countdown', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.verifyEmail,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(message: 'Too many requests', code: 429),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.enterText(findCodeField(), '123456');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findRateLimitIcon(), findsOneWidget);
      expect(find.text('Rate Limit Exceeded'), findsOneWidget);
    });
  });

  group('OtpVerificationScreen - Resend Functionality', () {
    testWidgets('test_resend_otp_success_shows_snackbar', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.resendOtp,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {'message': 'Code sent'},
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.resendOtp),
        ),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.tap(findResendButton());
      await tester.pumpAndSettle();

      expect(find.text('Verification code sent successfully'), findsOneWidget);
    });

    testWidgets('test_resend_shows_cooldown_timer', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.resendOtp,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {'message': 'Code sent'},
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.resendOtp),
        ),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.tap(findResendButton());
      await tester.pumpAndSettle();

      // Should show cooldown timer
      expect(find.textContaining('Resend in'), findsOneWidget);
    });

    testWidgets('test_resend_rate_limit_shows_rate_limit_state',
        (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.resendOtp,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(message: 'Too many requests', code: 429),
      );

      await tester.pumpWidget(
        buildTestableOtpScreen(
          email: 'test@example.com',
          mockApiClient: mockApiClient,
          mockSecureStorage: mockSecureStorage,
          mockAuthNotifier: mockAuthNotifier,
        ),
      );

      await tester.tap(findResendButton());
      await tester.pumpAndSettle();

      expect(findRateLimitIcon(), findsOneWidget);
    });
  });
}
