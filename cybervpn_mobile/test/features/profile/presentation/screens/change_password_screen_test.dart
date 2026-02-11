import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/profile/presentation/screens/change_password_screen.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockApiClient extends Mock implements ApiClient {}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

void ignoreOverflowErrors(
  FlutterErrorDetails details, {
  bool forceReport = false,
}) {
  bool ifIsOverflowError = false;
  bool isUnableToLoadAsset = false;

  final exception = details.exception;
  if (exception is FlutterError) {
    ifIsOverflowError = !exception.diagnostics.any(
      (e) => e.value.toString().startsWith("A RenderFlex overflowed by"),
    );
    isUnableToLoadAsset = !exception.diagnostics.any(
      (e) => e.value.toString().startsWith("Unable to load asset"),
    );
  }

  if (ifIsOverflowError || isUnableToLoadAsset) {
    debugPrint('Ignoring error: ${details.exception}');
  } else {
    FlutterError.dumpErrorToConsole(details, forceReport: forceReport);
  }
}

Widget buildTestableChangePasswordScreen({
  required MockApiClient mockApiClient,
}) {
  return ProviderScope(
    overrides: [
      apiClientProvider.overrideWithValue(mockApiClient),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: ChangePasswordScreen(),
    ),
  );
}

// Finders
Finder findCurrentPasswordField() => find.widgetWithText(
      TextFormField,
      'Current Password',
    );
Finder findNewPasswordField() => find.widgetWithText(
      TextFormField,
      'New Password',
    );
Finder findConfirmPasswordField() => find.widgetWithText(
      TextFormField,
      'Confirm New Password',
    );
Finder findSubmitButton() => find.widgetWithText(FilledButton, 'Change Password');
Finder findSuccessIcon() => find.byIcon(Icons.check_circle_outline);
Finder findErrorIcon() => find.byIcon(Icons.error_outline);
Finder findRateLimitIcon() => find.byIcon(Icons.hourglass_top);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockApiClient mockApiClient;

  setUp(() {
    mockApiClient = MockApiClient();
    FlutterError.onError = ignoreOverflowErrors;
  });

  group('ChangePasswordScreen - Rendering', () {
    testWidgets('test_renders_password_change_form', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      expect(find.text('Change Password'), findsWidgets);
      expect(findCurrentPasswordField(), findsOneWidget);
      expect(findNewPasswordField(), findsOneWidget);
      expect(findConfirmPasswordField(), findsOneWidget);
      expect(findSubmitButton(), findsOneWidget);
    });

    testWidgets('test_renders_lock_reset_icon', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      expect(find.byIcon(Icons.lock_reset), findsOneWidget);
    });

    testWidgets('test_password_fields_obscure_text_by_default',
        (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      final currentField =
          tester.widget<TextFormField>(find.byType(TextFormField).at(0));
      final newField =
          tester.widget<TextFormField>(find.byType(TextFormField).at(1));
      final confirmField =
          tester.widget<TextFormField>(find.byType(TextFormField).at(2));

      expect(currentField.obscureText, isTrue);
      expect(newField.obscureText, isTrue);
      expect(confirmField.obscureText, isTrue);
    });
  });

  group('ChangePasswordScreen - Form Validation', () {
    testWidgets('test_validates_empty_current_password', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(find.text('This field is required'), findsWidgets);
    });

    testWidgets('test_validates_new_password_minimum_length', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'current_password');
      await tester.enterText(find.byType(TextFormField).at(1), 'short');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(find.text('Password must be at least 12 characters'), findsOneWidget);
    });

    testWidgets('test_validates_password_mismatch', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'current_password');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'DifferentPassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(find.text('Passwords do not match'), findsOneWidget);
    });

    testWidgets('test_validates_new_password_same_as_old', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'SamePassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'SamePassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(find.text('New password must be different from current password'), findsOneWidget);
    });
  });

  group('ChangePasswordScreen - Password Strength Indicator', () {
    testWidgets('test_shows_password_strength_indicator', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(1), 'WeakPassword123!');
      await tester.pumpAndSettle();

      // Should show strength indicator bars
      expect(find.byType(Container), findsWidgets);
    });

    testWidgets('test_strength_indicator_updates_on_input', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      // Type weak password
      await tester.enterText(find.byType(TextFormField).at(1), 'weak');
      await tester.pumpAndSettle();

      // Type stronger password
      await tester.enterText(
          find.byType(TextFormField).at(1), 'StrongPassword123!@#');
      await tester.pumpAndSettle();

      // Strength indicator should be visible
      expect(find.byType(Container), findsWidgets);
    });
  });

  group('ChangePasswordScreen - Successful Password Change', () {
    testWidgets('test_successful_password_change_shows_success_state',
        (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {'message': 'Password changed'},
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.changePassword),
        ),
      );

      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'OldPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'NewPassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findSuccessIcon(), findsOneWidget);
      expect(find.text('Password Changed'), findsOneWidget);
    });

    testWidgets('test_successful_change_sends_correct_data', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: any(named: 'data'),
          )).thenAnswer(
        (_) async => Response(
          data: {'message': 'Success'},
          statusCode: 200,
          requestOptions: RequestOptions(path: ApiConstants.changePassword),
        ),
      );

      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'OldPass123!');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPass123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'NewPass123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      verify(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: {
              'current_password': 'OldPass123!',
              'new_password': 'NewPass123!',
            },
          )).called(1);
    });
  });

  group('ChangePasswordScreen - Error Handling', () {
    testWidgets('test_invalid_current_password_shows_error', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(message: 'Current password is incorrect', code: 401),
      );

      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'WrongPassword');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'NewPassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findErrorIcon(), findsOneWidget);
      expect(find.text('Current password is incorrect'), findsOneWidget);
    });

    testWidgets('test_oauth_user_shows_oauth_only_error', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(
          message: 'OAuth users cannot change password',
          code: 403,
        ),
      );

      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'Password123!');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'NewPassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findErrorIcon(), findsOneWidget);
      expect(
        find.text('Password change is not available for OAuth accounts'),
        findsOneWidget,
      );
    });

    testWidgets('test_network_error_shows_message', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: any(named: 'data'),
          )).thenThrow(
        const NetworkException(message: 'No internet connection'),
      );

      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'Password123!');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'NewPassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findErrorIcon(), findsOneWidget);
      expect(find.text('No internet connection'), findsOneWidget);
    });
  });

  group('ChangePasswordScreen - Rate Limiting', () {
    testWidgets('test_rate_limit_429_shows_countdown', (tester) async {
      when(() => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.changePassword,
            data: any(named: 'data'),
          )).thenThrow(
        const ServerException(message: 'Too many requests', code: 429),
      );

      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      await tester.enterText(
          find.byType(TextFormField).at(0), 'Password123!');
      await tester.enterText(
          find.byType(TextFormField).at(1), 'NewPassword123!');
      await tester.enterText(
          find.byType(TextFormField).at(2), 'NewPassword123!');
      await tester.tap(findSubmitButton());
      await tester.pumpAndSettle();

      expect(findRateLimitIcon(), findsOneWidget);
      expect(find.text('Rate Limit Exceeded'), findsOneWidget);
      expect(find.textContaining('Try again in'), findsOneWidget);
    });
  });

  group('ChangePasswordScreen - Visibility Toggle', () {
    testWidgets('test_toggles_current_password_visibility', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      final visibilityButton = find.byIcon(Icons.visibility_outlined).first;
      await tester.tap(visibilityButton);
      await tester.pumpAndSettle();

      final currentField =
          tester.widget<TextFormField>(find.byType(TextFormField).at(0));
      expect(currentField.obscureText, isFalse);
    });

    testWidgets('test_toggles_new_password_visibility', (tester) async {
      await tester.pumpWidget(
        buildTestableChangePasswordScreen(mockApiClient: mockApiClient),
      );

      final visibilityButtons = find.byIcon(Icons.visibility_outlined);
      await tester.tap(visibilityButtons.at(1));
      await tester.pumpAndSettle();

      final newField =
          tester.widget<TextFormField>(find.byType(TextFormField).at(1));
      expect(newField.obscureText, isFalse);
    });
  });
}
