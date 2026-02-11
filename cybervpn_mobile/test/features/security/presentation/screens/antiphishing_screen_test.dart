import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/security/domain/entities/antiphishing_code.dart';
import 'package:cybervpn_mobile/features/security/domain/repositories/security_repository.dart';
import 'package:cybervpn_mobile/features/security/presentation/providers/antiphishing_provider.dart';
import 'package:cybervpn_mobile/features/security/presentation/screens/antiphishing_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockSecurityRepository extends Mock implements SecurityRepository {}

class MockAntiphishingCode extends AntiphishingCode {
  MockAntiphishingCode({
    required super.isSet,
    required super.code,
    required super.maskedCode,
  });
}

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

Widget buildTestableAntiphishingScreen({
  required MockSecurityRepository mockRepository,
  AsyncValue<AntiphishingCode>? codeOverride,
}) {
  return ProviderScope(
    overrides: [
      securityRepositoryProvider.overrideWithValue(mockRepository),
      if (codeOverride != null)
        antiphishingCodeProvider.overrideWith((ref) => codeOverride),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: AntiphishingScreen(),
    ),
  );
}

// Finders
Finder findSetCodeButton() => find.widgetWithText(FilledButton, 'Set Code');
Finder findEditCodeButton() => find.widgetWithText(FilledButton, 'Edit Code');
Finder findDeleteCodeButton() => find.widgetWithText(OutlinedButton, 'Delete Code');
Finder findSaveButton() => find.widgetWithText(FilledButton, 'Save');
Finder findCancelButton() => find.widgetWithText(TextButton, 'Cancel');
Finder findCodeField() => find.byType(TextFormField);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockSecurityRepository mockRepository;

  setUp(() {
    mockRepository = MockSecurityRepository();
    FlutterError.onError = ignoreOverflowErrors;
  });

  group('AntiphishingScreen - Rendering', () {
    testWidgets('test_renders_antiphishing_title', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Antiphishing Code'), findsWidgets);
    });

    testWidgets('test_loading_state_shows_progress_indicator', (tester) async {
      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: const AsyncValue.loading(),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('test_error_state_shows_error_message', (tester) async {
      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('An error occurred'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });
  });

  group('AntiphishingScreen - Not Set State', () {
    testWidgets('test_not_set_state_shows_message', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No Antiphishing Code Set'), findsOneWidget);
      expect(find.byIcon(Icons.security_outlined), findsOneWidget);
    });

    testWidgets('test_not_set_state_shows_set_button', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(findSetCodeButton(), findsOneWidget);
    });

    testWidgets('test_not_set_state_shows_explanation', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Set a code to verify official emails from CyberVPN'),
        findsOneWidget,
      );
    });
  });

  group('AntiphishingScreen - View Mode', () {
    testWidgets('test_view_mode_displays_masked_code', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('SEC****23'), findsOneWidget);
      expect(find.text('Current Code'), findsOneWidget);
    });

    testWidgets('test_view_mode_shows_edit_and_delete_buttons',
        (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(findEditCodeButton(), findsOneWidget);
      expect(findDeleteCodeButton(), findsOneWidget);
    });

    testWidgets('test_view_mode_shows_verified_user_icon', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.verified_user), findsOneWidget);
    });
  });

  group('AntiphishingScreen - Edit Mode', () {
    testWidgets('test_clicking_set_code_enters_edit_mode', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findSetCodeButton());
      await tester.pumpAndSettle();

      expect(findCodeField(), findsOneWidget);
      expect(findSaveButton(), findsOneWidget);
      expect(findCancelButton(), findsOneWidget);
    });

    testWidgets('test_clicking_edit_code_enters_edit_mode', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findEditCodeButton());
      await tester.pumpAndSettle();

      expect(findCodeField(), findsOneWidget);
      expect(findSaveButton(), findsOneWidget);
    });

    testWidgets('test_edit_mode_shows_edit_icon', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findSetCodeButton());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    });

    testWidgets('test_cancel_button_returns_to_view_mode', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findEditCodeButton());
      await tester.pumpAndSettle();

      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      expect(find.text('SEC****23'), findsOneWidget);
      expect(findEditCodeButton(), findsOneWidget);
    });
  });

  group('AntiphishingScreen - Form Validation', () {
    testWidgets('test_validates_empty_code', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findSetCodeButton());
      await tester.pumpAndSettle();

      await tester.tap(findSaveButton());
      await tester.pumpAndSettle();

      expect(find.text('This field is required'), findsOneWidget);
    });

    testWidgets('test_validates_code_too_long', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findSetCodeButton());
      await tester.pumpAndSettle();

      await tester.enterText(
        findCodeField(),
        'a' * 51, // 51 characters (max is 50)
      );
      await tester.tap(findSaveButton());
      await tester.pumpAndSettle();

      expect(find.text('Code must be 50 characters or less'), findsOneWidget);
    });
  });

  group('AntiphishingScreen - Save Code', () {
    testWidgets('test_successful_save_returns_to_view_mode', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      when(() => mockRepository.setAntiphishingCode(any())).thenAnswer(
        (_) async => Result.success(null),
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findSetCodeButton());
      await tester.pumpAndSettle();

      await tester.enterText(findCodeField(), 'MySecretCode123');
      await tester.tap(findSaveButton());
      await tester.pumpAndSettle();

      verify(() => mockRepository.setAntiphishingCode('MySecretCode123'))
          .called(1);
    });

    testWidgets('test_save_error_shows_error_message', (tester) async {
      final code = MockAntiphishingCode(
        isSet: false,
        code: null,
        maskedCode: '',
      );

      when(() => mockRepository.setAntiphishingCode(any())).thenAnswer(
        (_) async => Result.failure(
          const AppFailure.server(message: 'Failed to save'),
        ),
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findSetCodeButton());
      await tester.pumpAndSettle();

      await tester.enterText(findCodeField(), 'MySecretCode123');
      await tester.tap(findSaveButton());
      await tester.pumpAndSettle();

      expect(find.text('Failed to save'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });
  });

  group('AntiphishingScreen - Delete Code', () {
    testWidgets('test_delete_button_shows_confirmation_dialog',
        (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findDeleteCodeButton());
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('Delete Antiphishing Code?'), findsOneWidget);
    });

    testWidgets('test_delete_confirmation_can_be_cancelled', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findDeleteCodeButton());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsNothing);
      expect(find.text('SEC****23'), findsOneWidget);
    });

    testWidgets('test_delete_confirmation_deletes_code', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      when(() => mockRepository.deleteAntiphishingCode()).thenAnswer(
        (_) async => Result.success(null),
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findDeleteCodeButton());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();

      verify(() => mockRepository.deleteAntiphishingCode()).called(1);
    });

    testWidgets('test_delete_error_shows_error_message', (tester) async {
      final code = MockAntiphishingCode(
        isSet: true,
        code: 'SECRET123',
        maskedCode: 'SEC****23',
      );

      when(() => mockRepository.deleteAntiphishingCode()).thenAnswer(
        (_) async => Result.failure(
          const AppFailure.server(message: 'Failed to delete'),
        ),
      );

      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride: AsyncValue.data(code),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findDeleteCodeButton());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();

      expect(find.text('Failed to delete'), findsOneWidget);
    });
  });

  group('AntiphishingScreen - Error Recovery', () {
    testWidgets('test_error_state_shows_retry_button', (tester) async {
      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(FilledButton, 'Retry'), findsOneWidget);
    });

    testWidgets('test_error_state_shows_close_button', (tester) async {
      await tester.pumpWidget(
        buildTestableAntiphishingScreen(
          mockRepository: mockRepository,
          codeOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(TextButton, 'Close'), findsOneWidget);
    });
  });
}
