# PRD: Исправление Onboarding Flow в CyberVPN Mobile

**Дата:** 7 февраля 2026
**Статус:** Draft
**Приоритет:** Critical
**Автор:** Gemini CLI (Assistant)

## 1. Обзор
Данный документ описывает план исправлений критических ошибок в модуле Onboarding мобильного приложения `cybervpn_mobile`.
В текущей версии наблюдаются две блокирующие проблемы:
1.  **Ошибка запуска:** Экран Onboarding не открывается автоматически после Splash Screen (требуется взаимодействие пользователя).
2.  **Блокировка навигации:** Кнопки "Skip" и "Get Started" не выполняют переход на следующий экран (приложение остается на Onboarding).

## 2. Анализ Проблем (Root Cause Analysis)

### 2.1. Проблема "Не открывается сразу" (Race Condition)
*   **Симптом:** После запуска приложение может пропустить проверку необходимости Onboarding или зависнуть на Splash Screen до нажатия кнопки.
*   **Причина:** В `lib/app/router/app_router.dart`, логика редиректа проверяет только `isAuthLoading`. Провайдер `shouldShowOnboardingProvider` является `FutureProvider`, и в момент инициализации роутера он может находиться в состоянии `Loading`.
*   **Механизм сбоя:**
    ```dart
    // app_router.dart
    final shouldShowOnboarding = ref.read(shouldShowOnboardingProvider).value ?? false;
    ```
    Если провайдер еще загружается, возвращается `false` (значение по умолчанию). Роутер считает, что Onboarding не нужен, и пытается перейти на `/login` или `/connection`. Когда провайдер загружается (становится `true`), роутер обновляется (благодаря `ref.listen`), но первоначальный "скачок" уже произошел, что вызывает UI глитчи или некорректное состояние.

### 2.2. Проблема "Кнопки не работают" (State Stale)
*   **Симптом:** При нажатии "Skip" или "Get Started" ничего не происходит.
*   **Причина:** Рассинхронизация между состоянием `OnboardingNotifier` и `shouldShowOnboardingProvider`.
*   **Механизм сбоя:**
    1.  Пользователь нажимает "Skip".
    2.  `OnboardingNotifier` обновляет хранилище (`isComplete = true`), но **не обновляет** `shouldShowOnboardingProvider`.
    3.  Вызывается `context.go('/permissions')`.
    4.  Срабатывает Guard в `app_router.dart`.
    5.  Он читает `shouldShowOnboardingProvider`, который **всё ещё хранит закешированное значение `true`** (показать onboarding).
    6.  Роутер принудительно возвращает пользователя на `/onboarding`.
*   **Решение:** Необходимо инвалидировать `shouldShowOnboardingProvider` после изменения состояния в `OnboardingNotifier`.

### 2.3. Проблема UI Синхронизации
*   **Симптом:** Сложная и хрупкая логика в `_onPageChanged` внутри `OnboardingScreen`.
*   **Причина:** Попытка ручной синхронизации индекса `PageView` с состоянием Riverpod через циклы `nextPage()`/`previousPage()`. Это может вызывать лишние перерисовки и рассинхронизацию анимаций.

### 2.4. Проблема с клавиатурой на LoginScreen
*   **Симптом:** При переходе на экран логина поле Email становится активным (фокус установлен), но экранная клавиатура не появляется.
*   **Причина:** Использование параметра `autofocus: true` в `TextFormField`. На многих современных версиях Android/iOS системные политики запрещают автоматическое открытие клавиатуры без явного взаимодействия пользователя (tap) для предотвращения плохого UX. Фокус захватывается виджетом, но сигнал на открытие IME блокируется ОС или не отправляется Flutter-ом корректно в момент построения дерева.
*   **Решение:** Отключить `autofocus: true`. Это стандартный паттерн для мобильных приложений — клавиатура должна открываться только по явному нажатию пользователя на поле ввода.

### 2.5. Не работает "Forgot password?"
*   **Симптом:** Нажатие на кнопку "Forgot password?" не вызывает никакой реакции.
*   **Причина:** Функционал отсутствует в коде. В `LoginScreen` (стр. 258) установлен пустой callback с комментарием `// TODO: implement forgot-password flow`.
*   **Решение:** Требуется реализация экрана восстановления пароля и соответствующего метода в `AuthProvider` / `AuthRepository`.

## 3. Технические Требования (Fix Plan)

### 3.1. Исправление Роутинга (app_router.dart)
Необходимо добавить ожидание загрузки состояния Onboarding в логику Splash.

**Изменения:**
1.  В `app_router.dart` внутри `redirect`:
    *   Проверять `shouldShowOnboardingProvider.isLoading`.
    *   Если `isLoading` == `true`, возвращать `null` (оставаться на Splash), аналогично проверке `isAuthLoading`.

### 3.2. Исправление State Management (onboarding_provider.dart)
Необходимо связать изменение состояния завершения с провайдером проверки.

**Изменения:**
1.  В методах `skip()` и `complete()` класса `OnboardingNotifier`:
    *   Добавить вызов `ref.invalidate(shouldShowOnboardingProvider)` в конец метода (после успешного выполнения в репозитории).
    *   Это заставит `FutureProvider` перезапросить данные из репозитория, получить актуальное `false` и триггернуть обновление роутера.

### 3.3. Рефакторинг UI (onboarding_screen.dart)
Упростить управление состоянием страницы.

**Изменения:**
1.  Использовать `PageController` как единственный источник истины для текущего индекса страницы в UI.
2.  Убрать сложную логику синхронизации в `_onPageChanged`. Просто обновлять индекс в провайдере (если он нужен для индикатора) или использовать локальный `setState` для индикатора, если глобальный стейт индекса не используется другими экранами.
3.  Исправить типизацию callback-ов кнопок (убрать `Future` из `onPressed`, обрабатывать ошибки внутри).

### 3.4. Исправление UI Логина (login_form.dart)
**Изменения:**
1.  В файле `lib/features/auth/presentation/widgets/login_form.dart`:
    *   Найти поле Email (`TextFormField`).
    *   Удалить строку `autofocus: true`.

### 3.5. Реализация Forgot Password (Stub)
**Изменения:**
1.  В `app_router.dart`: Добавить новый маршрут `/forgot-password`.
2.  В `LoginScreen`: Обновить `onForgotPassword`, добавив навигацию `context.push('/forgot-password')`.
3.  Создать заглушку экрана `lib/features/auth/presentation/screens/forgot_password_screen.dart` (текст "Coming Soon" или форма отправки email), чтобы кнопка не казалась сломанной. *Примечание: Полная реализация требует Backend API, в рамках этой задачи делаем UI-заглушку или базовую верстку.*

## 4. План Реализации (Tasks)

### Задача 1: Fix Router Loading State
*   **Файл:** `lib/app/router/app_router.dart`
*   **Действие:** Добавить проверку `ref.read(shouldShowOnboardingProvider).isLoading` в начало функции `redirect`.

### Задача 2: Fix Provider Invalidation
*   **Файл:** `lib/features/onboarding/presentation/providers/onboarding_provider.dart`
*   **Действие:** Добавить `ref.invalidate(shouldShowOnboardingProvider)` в конец методов `skip()` и `complete()`.

### Задача 3: Refactor Onboarding Screen
*   **Файл:** `lib/features/onboarding/presentation/screens/onboarding_screen.dart`
*   **Действие:**
    *   Упростить `_onPageChanged`.
    *   Обернуть вызовы `_handleSkip` и `_handleGetStarted` в `try-catch` с показом ошибки (SnackBar), если что-то пойдет не так.

### Задача 4: Fix Login UI & Forgot Password Stub
*   **Файлы:** `login_form.dart`, `app_router.dart`, `login_screen.dart`
*   **Действие:**
    *   Убрать `autofocus` в `LoginForm`.
    *   Добавить роут `/forgot-password` в `app_router.dart`.
    *   Привязать навигацию к кнопке "Forgot Password".
    *   Создать базовый экран `ForgotPasswordScreen`.

## 5. Использованные Skills & Best Practices

*   **flutter-riverpod-expert:**
    *   Использование `ref.invalidate` для сброса закешированных провайдеров (Self-refresh pattern).
    *   Правильная обработка `AsyncValue` в UI.
*   **flutter-navigation (GoRouter):**
    *   Использование `redirect` guards для управления доступом.
    *   Предотвращение "redirect loops" путем проверки состояния загрузки всех зависимостей.
*   **flutter-animations:**
    *   Использование `AnimatedOpacity` и `AnimatedSwitcher` для плавного скрытия кнопок (уже реализовано, сохранить при рефакторинге).
*   **flutter-adaptive-ui:**
    *   Сохранение адаптивности верстки (SafeArea, использование токенов отступов).

5.  [ ] На экране Login поле Email не захватывает фокус автоматически при открытии, клавиатура не перекрывает контент самопроизвольно.
6.  [ ] Нажатие "Forgot password?" открывает экран восстановления (или заглушку).

## 6. Критерии Приемки (Definition of Done)
1.  [ ] При "чистом" запуске приложения (после очистки данных) Splash Screen висит ровно столько, сколько нужно для загрузки Auth и Onboarding check, затем **автоматически** переходит на Onboarding.
2.  [ ] На экране Onboarding кнопка "Skip" перебрасывает на `/permissions` (или следующий по логике экран).
3.  [ ] На экране Onboarding кнопка "Get Started" перебрасывает на `/permissions`.
4.  [ ] При повторном запуске Onboarding не показывается.
