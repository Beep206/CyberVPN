import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/link_social_account.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/unlink_social_account.dart';

import '../../../../helpers/mock_repositories.dart';

void main() {
  late MockProfileRepository mockRepository;

  setUpAll(() {
    registerFallbackValue(OAuthProvider.google);
  });

  setUp(() {
    mockRepository = MockProfileRepository();
  });

  // ---------------------------------------------------------------------------
  // LinkSocialAccountUseCase
  // ---------------------------------------------------------------------------
  group('LinkSocialAccountUseCase', () {
    late LinkSocialAccountUseCase useCase;

    setUp(() {
      useCase = LinkSocialAccountUseCase(mockRepository);
    });

    test('returns auth URL when provider is not yet linked',
        () async {
      // Arrange
      when(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.github))
          .thenAnswer((_) async => const Success('https://auth.example.com/github'));

      // Act
      final result = await useCase(
        provider: OAuthProvider.github,
        currentlyLinked: const [OAuthProvider.google],
      );

      // Assert
      expect(result, isA<Success<String>>());
      expect((result as Success<String>).data, equals('https://auth.example.com/github'));
      verify(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.github)).called(1);
    });

    test('throws StateError when provider is already linked', () async {
      // Act & Assert
      await expectLater(
        () => useCase(
          provider: OAuthProvider.github,
          currentlyLinked: const [
            OAuthProvider.github,
            OAuthProvider.google,
          ],
        ),
        throwsA(isA<StateError>()),
      );
      verifyNever(() => mockRepository.getOAuthAuthorizationUrl(any()));
    });

    test('allows linking when currentlyLinked is empty', () async {
      // Arrange
      when(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.google))
          .thenAnswer((_) async => const Success('https://auth.example.com/google'));

      // Act
      final result = await useCase(
        provider: OAuthProvider.google,
        currentlyLinked: const [],
      );

      // Assert
      expect(result, isA<Success<String>>());
      expect((result as Success<String>).data, equals('https://auth.example.com/google'));
      verify(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.google)).called(1);
    });

    test('links each provider individually', () async {
      // Arrange
      when(() => mockRepository.getOAuthAuthorizationUrl(any()))
          .thenAnswer((_) async => const Success('https://auth.example.com/provider'));

      // Act: link all providers sequentially
      for (final provider in OAuthProvider.values) {
        await useCase(
          provider: provider,
          currentlyLinked: const [],
        );
      }

      // Assert: each provider was linked exactly once
      for (final provider in OAuthProvider.values) {
        verify(() => mockRepository.getOAuthAuthorizationUrl(provider)).called(1);
      }
    });

    test('propagates repository exceptions', () async {
      // Arrange
      when(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.apple))
          .thenThrow(Exception('OAuth error'));

      // Act & Assert
      expect(
        () => useCase(
          provider: OAuthProvider.apple,
          currentlyLinked: const [],
        ),
        throwsA(isA<Exception>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // UnlinkSocialAccountUseCase
  // ---------------------------------------------------------------------------
  group('UnlinkSocialAccountUseCase', () {
    late UnlinkSocialAccountUseCase useCase;

    setUp(() {
      useCase = UnlinkSocialAccountUseCase(mockRepository);
    });

    test('calls repository.unlinkOAuth when provider is linked', () async {
      // Arrange
      when(() => mockRepository.unlinkOAuth(OAuthProvider.google))
          .thenAnswer((_) async => const Success<void>(null));

      // Act
      await useCase(
        provider: OAuthProvider.google,
        currentlyLinked: const [
          OAuthProvider.google,
          OAuthProvider.telegram,
        ],
      );

      // Assert
      verify(() => mockRepository.unlinkOAuth(OAuthProvider.google)).called(1);
    });

    test('throws StateError when provider is not linked', () async {
      // Act & Assert
      await expectLater(
        () => useCase(
          provider: OAuthProvider.apple,
          currentlyLinked: const [OAuthProvider.google],
        ),
        throwsA(isA<StateError>()),
      );
      verifyNever(() => mockRepository.unlinkOAuth(any()));
    });

    test('throws StateError when currentlyLinked is empty', () async {
      await expectLater(
        () => useCase(
          provider: OAuthProvider.github,
          currentlyLinked: const [],
        ),
        throwsA(isA<StateError>()),
      );
    });

    test('propagates repository exceptions', () async {
      // Arrange
      when(() => mockRepository.unlinkOAuth(OAuthProvider.telegram))
          .thenThrow(Exception('Unlink error'));

      // Act & Assert
      expect(
        () => useCase(
          provider: OAuthProvider.telegram,
          currentlyLinked: const [OAuthProvider.telegram],
          hasEmailPassword: true,
        ),
        throwsA(isA<Exception>()),
      );
    });

    test('throws StateError when only login method and no email', () async {
      // Telegram is the only linked provider, no email/password
      await expectLater(
        () => useCase(
          provider: OAuthProvider.telegram,
          currentlyLinked: const [OAuthProvider.telegram],
          hasEmailPassword: false,
        ),
        throwsA(isA<StateError>()),
      );
      verifyNever(() => mockRepository.unlinkOAuth(any()));
    });

    test('allows unlink when only provider but has email/password', () async {
      when(() => mockRepository.unlinkOAuth(OAuthProvider.telegram))
          .thenAnswer((_) async => const Success<void>(null));

      await useCase(
        provider: OAuthProvider.telegram,
        currentlyLinked: const [OAuthProvider.telegram],
        hasEmailPassword: true,
      );

      verify(() => mockRepository.unlinkOAuth(OAuthProvider.telegram)).called(1);
    });

    test('allows unlink when other providers linked even without email', () async {
      when(() => mockRepository.unlinkOAuth(OAuthProvider.telegram))
          .thenAnswer((_) async => const Success<void>(null));

      await useCase(
        provider: OAuthProvider.telegram,
        currentlyLinked: const [OAuthProvider.telegram, OAuthProvider.github],
        hasEmailPassword: false,
      );

      verify(() => mockRepository.unlinkOAuth(OAuthProvider.telegram)).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Full OAuth lifecycle: link -> unlink
  // ---------------------------------------------------------------------------
  group('Full OAuth lifecycle', () {
    late LinkSocialAccountUseCase linkUseCase;
    late UnlinkSocialAccountUseCase unlinkUseCase;

    setUp(() {
      linkUseCase = LinkSocialAccountUseCase(mockRepository);
      unlinkUseCase = UnlinkSocialAccountUseCase(mockRepository);
    });

    test('link then unlink the same provider succeeds', () async {
      // Arrange
      when(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.github))
          .thenAnswer((_) async => const Success('https://auth.example.com/github'));
      when(() => mockRepository.unlinkOAuth(OAuthProvider.github))
          .thenAnswer((_) async => const Success<void>(null));

      // Act: link
      await linkUseCase(
        provider: OAuthProvider.github,
        currentlyLinked: const [],
      );

      // Act: unlink (simulating updated linked list, with email as alternative)
      await unlinkUseCase(
        provider: OAuthProvider.github,
        currentlyLinked: const [OAuthProvider.github],
        hasEmailPassword: true,
      );

      // Assert
      verify(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.github)).called(1);
      verify(() => mockRepository.unlinkOAuth(OAuthProvider.github)).called(1);
    });

    test('cannot link an already-linked provider', () async {
      // Arrange
      when(() => mockRepository.getOAuthAuthorizationUrl(OAuthProvider.google))
          .thenAnswer((_) async => const Success('https://auth.example.com/google'));

      // Act: link first time
      await linkUseCase(
        provider: OAuthProvider.google,
        currentlyLinked: const [],
      );

      // Act: try to link again (simulating updated linked list)
      await expectLater(
        () => linkUseCase(
          provider: OAuthProvider.google,
          currentlyLinked: const [OAuthProvider.google],
        ),
        throwsA(isA<StateError>()),
      );
    });

    test('cannot unlink a provider that is not linked', () async {
      await expectLater(
        () => unlinkUseCase(
          provider: OAuthProvider.apple,
          currentlyLinked: const [OAuthProvider.google, OAuthProvider.github],
        ),
        throwsA(isA<StateError>()),
      );
    });
  });
}
