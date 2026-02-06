// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appName => 'CyberVPN';

  @override
  String get login => 'Войти';

  @override
  String get register => 'Регистрация';

  @override
  String get email => 'Эл. почта';

  @override
  String get password => 'Пароль';

  @override
  String get confirmPassword => 'Подтвердите пароль';

  @override
  String get forgotPassword => 'Забыли пароль?';

  @override
  String get orContinueWith => 'Или продолжить с';

  @override
  String get connect => 'Подключить';

  @override
  String get disconnect => 'Отключить';

  @override
  String get connecting => 'Подключение...';

  @override
  String get disconnecting => 'Отключение...';

  @override
  String get connected => 'Подключено';

  @override
  String get disconnected => 'Отключено';

  @override
  String get servers => 'Серверы';

  @override
  String get subscription => 'Подписка';

  @override
  String get settings => 'Настройки';

  @override
  String get profile => 'Профиль';

  @override
  String get selectServer => 'Выбрать сервер';

  @override
  String get autoSelect => 'Автовыбор';

  @override
  String get fastestServer => 'Быстрейший сервер';

  @override
  String get nearestServer => 'Ближайший сервер';

  @override
  String get killSwitch => 'Kill Switch';

  @override
  String get splitTunneling => 'Раздельное туннелирование';

  @override
  String get autoConnect => 'Автоподключение';

  @override
  String get language => 'Язык';

  @override
  String get theme => 'Тема';

  @override
  String get darkMode => 'Тёмная тема';

  @override
  String get lightMode => 'Светлая тема';

  @override
  String get systemDefault => 'Системная';

  @override
  String get logout => 'Выйти';

  @override
  String get logoutConfirm => 'Вы уверены, что хотите выйти?';

  @override
  String get cancel => 'Отмена';

  @override
  String get confirm => 'Подтвердить';

  @override
  String get retry => 'Повторить';

  @override
  String get errorOccurred => 'Произошла ошибка';

  @override
  String get noInternet => 'Нет подключения к интернету';

  @override
  String get downloadSpeed => 'Загрузка';

  @override
  String get uploadSpeed => 'Отдача';

  @override
  String get connectionTime => 'Время подключения';

  @override
  String get dataUsed => 'Использовано данных';

  @override
  String get currentPlan => 'Текущий план';

  @override
  String get upgradePlan => 'Улучшить план';

  @override
  String daysRemaining(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Осталось $count дней',
      many: 'Осталось $count дней',
      few: 'Осталось $count дня',
      one: 'Остался $count день',
    );
    return '$_temp0';
  }

  @override
  String get referral => 'Реферал';

  @override
  String get shareReferralCode => 'Поделиться реферальным кодом';

  @override
  String get support => 'Поддержка';

  @override
  String get privacyPolicy => 'Политика конфиденциальности';

  @override
  String get termsOfService => 'Условия использования';

  @override
  String version(String version) {
    return 'Версия $version';
  }

  @override
  String get onboardingWelcomeTitle => 'Добро пожаловать в CyberVPN';

  @override
  String get onboardingWelcomeDescription =>
      'Безопасный, быстрый и приватный доступ в интернет у вас под рукой.';

  @override
  String get onboardingFeaturesTitle => 'Мощные возможности';

  @override
  String get onboardingFeaturesDescription =>
      'Kill Switch, раздельное туннелирование и шифрование военного уровня для вашей защиты.';

  @override
  String get onboardingPrivacyTitle => 'Ваша приватность важна';

  @override
  String get onboardingPrivacyDescription =>
      'Политика нулевых логов. Мы никогда не отслеживаем, не сохраняем и не передаём ваши данные.';

  @override
  String get onboardingSpeedTitle => 'Молниеносная скорость';

  @override
  String get onboardingSpeedDescription =>
      'Подключайтесь к оптимизированным серверам по всему миру для максимальной скорости.';

  @override
  String get onboardingSkip => 'Пропустить';

  @override
  String get onboardingNext => 'Далее';

  @override
  String get onboardingGetStarted => 'Начать';

  @override
  String get onboardingBack => 'Назад';

  @override
  String onboardingPageIndicator(int current, int total) {
    return 'Страница $current из $total';
  }

  @override
  String get settingsTitle => 'Настройки';

  @override
  String get settingsGeneral => 'Основные';

  @override
  String get settingsVpn => 'Настройки VPN';

  @override
  String get settingsAppearance => 'Оформление';

  @override
  String get settingsDebug => 'Отладка';

  @override
  String get settingsNotifications => 'Уведомления';

  @override
  String get settingsAbout => 'О приложении';

  @override
  String get settingsVpnProtocolLabel => 'Протокол';

  @override
  String get settingsVpnProtocolDescription =>
      'Выберите протокол VPN для подключения.';

  @override
  String get settingsAutoConnectLabel => 'Автоподключение';

  @override
  String get settingsAutoConnectDescription =>
      'Автоматически подключаться при запуске приложения.';

  @override
  String get settingsKillSwitchLabel => 'Kill Switch';

  @override
  String get settingsKillSwitchDescription =>
      'Блокировать интернет при разрыве VPN-соединения.';

  @override
  String get settingsDnsLabel => 'Пользовательский DNS';

  @override
  String get settingsDnsDescription =>
      'Использовать пользовательский DNS-сервер.';

  @override
  String get settingsDnsPlaceholder => 'Введите адрес DNS';

  @override
  String get settingsSplitTunnelingLabel => 'Раздельное туннелирование';

  @override
  String get settingsSplitTunnelingDescription =>
      'Выберите, какие приложения используют VPN-соединение.';

  @override
  String get settingsThemeModeLabel => 'Тема оформления';

  @override
  String get settingsThemeModeDescription =>
      'Выберите светлую, тёмную или системную тему.';

  @override
  String get settingsLanguageLabel => 'Язык';

  @override
  String get settingsLanguageDescription => 'Выберите предпочитаемый язык.';

  @override
  String get settingsDebugLogsLabel => 'Журнал отладки';

  @override
  String get settingsDebugLogsDescription =>
      'Включить подробное логирование для диагностики.';

  @override
  String get settingsExportLogsLabel => 'Экспорт логов';

  @override
  String get settingsExportLogsDescription =>
      'Экспортировать логи отладки для поддержки.';

  @override
  String get settingsResetLabel => 'Сбросить настройки';

  @override
  String get settingsResetDescription =>
      'Восстановить все настройки по умолчанию.';

  @override
  String get settingsResetConfirm =>
      'Вы уверены, что хотите сбросить все настройки?';

  @override
  String get settingsStartOnBootLabel => 'Запуск при загрузке';

  @override
  String get settingsStartOnBootDescription =>
      'Автоматически запускать CyberVPN при включении устройства.';

  @override
  String get settingsConnectionTimeoutLabel => 'Тайм-аут подключения';

  @override
  String get settingsConnectionTimeoutDescription =>
      'Максимальное время ожидания при попытке подключения.';

  @override
  String settingsConnectionTimeoutSeconds(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count секунд',
      many: '$count секунд',
      few: '$count секунды',
      one: '$count секунда',
    );
    return '$_temp0';
  }

  @override
  String get profileDashboard => 'Панель профиля';

  @override
  String get profileEditProfile => 'Редактировать профиль';

  @override
  String get profileDisplayName => 'Отображаемое имя';

  @override
  String get profileEmailAddress => 'Адрес эл. почты';

  @override
  String get profileChangePassword => 'Изменить пароль';

  @override
  String get profileCurrentPassword => 'Текущий пароль';

  @override
  String get profileNewPassword => 'Новый пароль';

  @override
  String get profileConfirmNewPassword => 'Подтвердите новый пароль';

  @override
  String get profileTwoFactorAuth => 'Двухфакторная аутентификация';

  @override
  String get profileTwoFactorAuthDescription =>
      'Добавьте дополнительный уровень защиты вашей учётной записи.';

  @override
  String get profileTwoFactorEnable => 'Включить 2FA';

  @override
  String get profileTwoFactorDisable => 'Отключить 2FA';

  @override
  String get profileTwoFactorSetup => 'Настройка двухфакторной аутентификации';

  @override
  String get profileTwoFactorScanQr =>
      'Отсканируйте этот QR-код в приложении-аутентификаторе.';

  @override
  String get profileTwoFactorEnterCode =>
      'Введите 6-значный код из приложения-аутентификатора.';

  @override
  String get profileTwoFactorBackupCodes => 'Резервные коды';

  @override
  String get profileTwoFactorBackupCodesDescription =>
      'Сохраните эти коды в надёжном месте. Вы сможете использовать их для входа, если потеряете доступ к приложению-аутентификатору.';

  @override
  String get profileOauthAccounts => 'Привязанные аккаунты';

  @override
  String get profileOauthAccountsDescription =>
      'Управление привязанными аккаунтами социальных сетей.';

  @override
  String get profileOauthLink => 'Привязать аккаунт';

  @override
  String get profileOauthUnlink => 'Отвязать';

  @override
  String get profileOauthUnlinkConfirm =>
      'Вы уверены, что хотите отвязать этот аккаунт?';

  @override
  String get profileTrustedDevices => 'Доверенные устройства';

  @override
  String get profileTrustedDevicesDescription =>
      'Управление устройствами с доступом к вашей учётной записи.';

  @override
  String get profileDeviceCurrent => 'Текущее устройство';

  @override
  String profileDeviceLastActive(String date) {
    return 'Последняя активность $date';
  }

  @override
  String get profileDeviceRevoke => 'Отозвать доступ';

  @override
  String get profileDeviceRevokeConfirm =>
      'Вы уверены, что хотите отозвать доступ для этого устройства?';

  @override
  String get profileDeviceRevokeAll => 'Отозвать все устройства';

  @override
  String get profileDeleteAccount => 'Удалить аккаунт';

  @override
  String get profileDeleteAccountDescription =>
      'Безвозвратно удалить вашу учётную запись и все связанные данные.';

  @override
  String get profileDeleteAccountConfirm =>
      'Вы уверены, что хотите удалить свой аккаунт? Это действие нельзя отменить.';

  @override
  String get profileDeleteAccountButton => 'Удалить мой аккаунт';

  @override
  String get profileSubscriptionStatus => 'Статус подписки';

  @override
  String profileMemberSince(String date) {
    return 'Участник с $date';
  }

  @override
  String get configImportTitle => 'Импорт конфигурации';

  @override
  String get configImportQrScanTitle => 'Сканирование QR-кода';

  @override
  String get configImportQrScanDescription =>
      'Наведите камеру на QR-код конфигурации VPN.';

  @override
  String get configImportScanQrButton => 'Сканировать QR-код';

  @override
  String get configImportFromClipboard => 'Импорт из буфера обмена';

  @override
  String get configImportFromClipboardDescription =>
      'Вставьте ссылку или текст конфигурации из буфера обмена.';

  @override
  String get configImportFromFile => 'Импорт из файла';

  @override
  String get configImportFromFileDescription =>
      'Выберите файл конфигурации на вашем устройстве.';

  @override
  String get configImportPreviewTitle => 'Предпросмотр конфигурации';

  @override
  String get configImportPreviewServer => 'Сервер';

  @override
  String get configImportPreviewProtocol => 'Протокол';

  @override
  String get configImportPreviewPort => 'Порт';

  @override
  String get configImportConfirmButton => 'Импортировать конфигурацию';

  @override
  String get configImportCancelButton => 'Отменить импорт';

  @override
  String get configImportSuccess => 'Конфигурация успешно импортирована.';

  @override
  String get configImportError => 'Не удалось импортировать конфигурацию.';

  @override
  String get configImportInvalidFormat => 'Неверный формат конфигурации.';

  @override
  String get configImportDuplicate => 'Эта конфигурация уже существует.';

  @override
  String get configImportCameraPermission =>
      'Для сканирования QR-кодов необходим доступ к камере.';

  @override
  String get notificationCenterTitle => 'Уведомления';

  @override
  String get notificationCenterEmpty => 'Уведомлений пока нет.';

  @override
  String get notificationCenterMarkAllRead => 'Отметить все как прочитанные';

  @override
  String get notificationCenterClearAll => 'Очистить все';

  @override
  String get notificationTypeConnectionStatus => 'Статус подключения';

  @override
  String get notificationTypeServerSwitch => 'Смена сервера';

  @override
  String get notificationTypeSubscriptionExpiry => 'Истечение подписки';

  @override
  String get notificationTypeSecurityAlert => 'Предупреждение безопасности';

  @override
  String get notificationTypePromotion => 'Акция';

  @override
  String get notificationTypeSystemUpdate => 'Обновление системы';

  @override
  String notificationConnected(String serverName) {
    return 'Подключено к $serverName';
  }

  @override
  String get notificationDisconnected => 'VPN отключён.';

  @override
  String notificationServerSwitched(String serverName) {
    return 'Переключено на $serverName.';
  }

  @override
  String notificationSubscriptionExpiring(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count дней',
      many: '$count дней',
      few: '$count дня',
      one: '$count день',
    );
    return 'Ваша подписка истекает через $_temp0.';
  }

  @override
  String get notificationSubscriptionExpired =>
      'Ваша подписка истекла. Продлите её для продолжения использования CyberVPN.';

  @override
  String notificationUnreadCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count непрочитанных уведомлений',
      many: '$count непрочитанных уведомлений',
      few: '$count непрочитанных уведомления',
      one: '$count непрочитанное уведомление',
      zero: 'Нет непрочитанных уведомлений',
    );
    return '$_temp0';
  }

  @override
  String get referralDashboardTitle => 'Реферальная программа';

  @override
  String get referralDashboardDescription =>
      'Приглашайте друзей и получайте награды.';

  @override
  String get referralShareLink => 'Поделиться реферальной ссылкой';

  @override
  String get referralCopyLink => 'Копировать ссылку';

  @override
  String get referralLinkCopied =>
      'Реферальная ссылка скопирована в буфер обмена.';

  @override
  String get referralCodeLabel => 'Ваш реферальный код';

  @override
  String referralRewardsEarned(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count наград получено',
      many: '$count наград получено',
      few: '$count награды получено',
      one: '$count награда получена',
      zero: 'Нет полученных наград',
    );
    return '$_temp0';
  }

  @override
  String referralFriendsInvited(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count друзей приглашено',
      many: '$count друзей приглашено',
      few: '$count друга приглашено',
      one: '$count друг приглашён',
      zero: 'Нет приглашённых друзей',
    );
    return '$_temp0';
  }

  @override
  String referralRewardDescription(int days) {
    return 'Получите $days бесплатных дней за каждого друга, оформившего подписку.';
  }

  @override
  String get referralHistory => 'История рефералов';

  @override
  String get referralPending => 'В ожидании';

  @override
  String get referralCompleted => 'Завершено';

  @override
  String get referralExpired => 'Истекло';

  @override
  String get diagnosticsTitle => 'Диагностика';

  @override
  String get diagnosticsDescription =>
      'Проверьте подключение и устраните неполадки.';

  @override
  String get speedTestTitle => 'Тест скорости';

  @override
  String get speedTestStart => 'Начать тест скорости';

  @override
  String get speedTestRunning => 'Тестирование...';

  @override
  String get speedTestDownloadSpeed => 'Скорость загрузки';

  @override
  String get speedTestUploadSpeed => 'Скорость отдачи';

  @override
  String get speedTestPing => 'Пинг';

  @override
  String speedTestPingMs(int value) {
    return '$value мс';
  }

  @override
  String speedTestMbps(String value) {
    return '$value Мбит/с';
  }

  @override
  String get speedTestResult => 'Результат теста скорости';

  @override
  String get speedTestHistory => 'История тестов скорости';

  @override
  String get speedTestStepConnecting => 'Подключение к тестовому серверу...';

  @override
  String get speedTestStepDownload => 'Тестирование скорости загрузки...';

  @override
  String get speedTestStepUpload => 'Тестирование скорости отдачи...';

  @override
  String get speedTestStepPing => 'Измерение задержки...';

  @override
  String get speedTestStepComplete => 'Тест завершён.';

  @override
  String get speedTestNoVpn =>
      'Подключитесь к VPN перед запуском теста скорости.';

  @override
  String get logViewerTitle => 'Просмотр логов';

  @override
  String get logViewerEmpty => 'Логи недоступны.';

  @override
  String get logViewerExportButton => 'Экспортировать логи';

  @override
  String get logViewerClearButton => 'Очистить логи';

  @override
  String get logViewerClearConfirm =>
      'Вы уверены, что хотите очистить все логи?';

  @override
  String get logViewerFilterLabel => 'Фильтр';

  @override
  String get logViewerFilterAll => 'Все';

  @override
  String get logViewerFilterError => 'Ошибки';

  @override
  String get logViewerFilterWarning => 'Предупреждения';

  @override
  String get logViewerFilterInfo => 'Информация';

  @override
  String get logViewerCopied => 'Запись лога скопирована в буфер обмена.';

  @override
  String get logViewerExportSuccess => 'Логи успешно экспортированы.';

  @override
  String get logViewerExportError => 'Не удалось экспортировать логи.';

  @override
  String get widgetConnectLabel => 'Подключить VPN';

  @override
  String get widgetDisconnectLabel => 'Отключить VPN';

  @override
  String get widgetStatusLabel => 'Статус VPN';

  @override
  String get widgetServerLabel => 'Текущий сервер';

  @override
  String get quickActionConnect => 'Подключить';

  @override
  String get quickActionDisconnect => 'Отключить';

  @override
  String get quickActionServers => 'Серверы';

  @override
  String get quickActionSpeedTest => 'Тест скорости';

  @override
  String get quickActionSettings => 'Настройки';

  @override
  String get quickActionSupport => 'Поддержка';

  @override
  String get errorConnectionFailed =>
      'Не удалось подключиться. Попробуйте снова.';

  @override
  String get errorConnectionTimeout =>
      'Время подключения истекло. Проверьте соединение с интернетом.';

  @override
  String get errorServerUnavailable =>
      'Сервер временно недоступен. Попробуйте другой сервер.';

  @override
  String get errorInvalidConfig =>
      'Неверная конфигурация. Импортируйте настройки заново.';

  @override
  String get errorSubscriptionExpired =>
      'Ваша подписка истекла. Продлите её для продолжения работы.';

  @override
  String get errorSubscriptionRequired =>
      'Для использования этой функции необходима подписка.';

  @override
  String get errorAuthenticationFailed =>
      'Ошибка аутентификации. Войдите в систему снова.';

  @override
  String get errorTokenExpired => 'Сессия истекла. Войдите в систему снова.';

  @override
  String get errorNetworkUnreachable =>
      'Сеть недоступна. Проверьте подключение.';

  @override
  String get errorPermissionDenied => 'Доступ запрещён.';

  @override
  String get errorRateLimited => 'Слишком много запросов. Подождите немного.';

  @override
  String get errorUnexpected =>
      'Произошла непредвиденная ошибка. Попробуйте снова.';

  @override
  String get errorServerError => 'Ошибка сервера. Попробуйте позже.';

  @override
  String get errorInvalidCredentials => 'Неверный адрес эл. почты или пароль.';

  @override
  String get errorAccountLocked =>
      'Ваш аккаунт заблокирован. Обратитесь в службу поддержки.';

  @override
  String get errorWeakPassword =>
      'Пароль слишком слабый. Используйте минимум 8 символов, включая буквы и цифры.';

  @override
  String get errorEmailAlreadyInUse =>
      'Этот адрес эл. почты уже зарегистрирован.';

  @override
  String get errorInvalidEmail => 'Введите корректный адрес эл. почты.';

  @override
  String get errorFieldRequired => 'Это поле обязательно для заполнения.';

  @override
  String get errorPaymentFailed =>
      'Ошибка оплаты. Попробуйте снова или используйте другой способ оплаты.';

  @override
  String get errorQrScanFailed =>
      'Не удалось отсканировать QR-код. Попробуйте снова.';

  @override
  String get errorTelegramAuthCancelled => 'Вход через Telegram был отменён.';

  @override
  String get errorTelegramAuthFailed =>
      'Ошибка аутентификации через Telegram. Попробуйте снова.';

  @override
  String get errorTelegramAuthExpired =>
      'Время входа через Telegram истекло. Попробуйте снова.';

  @override
  String get errorTelegramNotInstalled =>
      'Telegram не установлен на этом устройстве.';

  @override
  String get errorTelegramAuthInvalid =>
      'Неверные данные аутентификации Telegram.';

  @override
  String get errorBiometricUnavailable =>
      'Биометрическая аутентификация недоступна на этом устройстве.';

  @override
  String get errorBiometricNotEnrolled =>
      'Биометрические данные не зарегистрированы. Настройте отпечаток пальца или распознавание лица в настройках устройства.';

  @override
  String get errorBiometricFailed =>
      'Ошибка биометрической аутентификации. Попробуйте снова.';

  @override
  String get errorBiometricLocked =>
      'Биометрическая аутентификация заблокирована. Попробуйте позже или используйте пароль.';

  @override
  String get errorSessionExpired =>
      'Ваша сессия истекла. Войдите в систему снова.';

  @override
  String get errorAccountDisabled =>
      'Ваш аккаунт отключён. Обратитесь в службу поддержки.';

  @override
  String errorRateLimitedWithCountdown(int seconds) {
    String _temp0 = intl.Intl.pluralLogic(
      seconds,
      locale: localeName,
      other: '$seconds секунд',
      many: '$seconds секунд',
      few: '$seconds секунды',
      one: '$seconds секунду',
    );
    return 'Слишком много попыток. Повторите через $_temp0.';
  }

  @override
  String get errorOfflineLoginRequired =>
      'Для входа требуется подключение к интернету. Проверьте соединение.';

  @override
  String get errorOfflineSessionExpired =>
      'Кэшированная сессия истекла. Подключитесь к интернету для входа.';

  @override
  String get a11yConnectButton => 'Подключиться к VPN-серверу';

  @override
  String get a11yDisconnectButton => 'Отключиться от VPN-сервера';

  @override
  String get a11yServerStatusOnline => 'Сервер в сети';

  @override
  String get a11yServerStatusOffline => 'Сервер не в сети';

  @override
  String get a11yServerStatusMaintenance => 'Сервер на обслуживании';

  @override
  String a11ySpeedIndicator(String speed) {
    return 'Текущая скорость: $speed';
  }

  @override
  String a11yConnectionStatus(String status) {
    return 'Статус подключения: $status';
  }

  @override
  String a11yServerSelect(String name, String country) {
    return 'Выбрать сервер $name в $country';
  }

  @override
  String get a11yNavigationMenu => 'Меню навигации';

  @override
  String get a11yCloseDialog => 'Закрыть диалог';

  @override
  String a11yToggleSwitch(String label) {
    return 'Переключить $label';
  }

  @override
  String a11yNotificationBadge(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count уведомлений',
      many: '$count уведомлений',
      few: '$count уведомления',
      one: '$count уведомление',
      zero: 'Нет уведомлений',
    );
    return '$_temp0';
  }

  @override
  String get a11yLoadingIndicator => 'Загрузка';

  @override
  String get a11yRefreshContent => 'Обновить содержимое';

  @override
  String get a11yBackButton => 'Назад';

  @override
  String get a11ySearchField => 'Поиск';

  @override
  String get rootDetectionDialogTitle => 'Rooted/Jailbroken Device Detected';

  @override
  String get rootDetectionDialogDescription =>
      'Your device appears to be rooted (Android) or jailbroken (iOS). While CyberVPN will continue to work, please note that using a rooted/jailbroken device may expose you to security risks.\n\nWe understand that users in censored regions often rely on rooted devices for additional privacy tools. CyberVPN will not block your access, but we recommend being cautious about the apps you install and the permissions you grant.';

  @override
  String get rootDetectionDialogDismiss => 'I Understand';

  @override
  String get loginEmailLabel => 'Email';

  @override
  String get loginEmailHint => 'Enter your email';

  @override
  String get loginPasswordLabel => 'Password';

  @override
  String get loginPasswordHint => 'Enter your password';

  @override
  String get loginShowPassword => 'Show password';

  @override
  String get loginHidePassword => 'Hide password';

  @override
  String get loginRememberMe => 'Remember me';

  @override
  String get loginButton => 'Login';

  @override
  String get loginContinueWithTelegram => 'Continue with Telegram';

  @override
  String get registerTitle => 'Create Account';

  @override
  String get registerSubtitle => 'Join CyberVPN for a secure experience';

  @override
  String get registerPasswordHint => 'Create a password';

  @override
  String get registerConfirmPasswordLabel => 'Confirm Password';

  @override
  String get registerConfirmPasswordHint => 'Re-enter your password';

  @override
  String get registerConfirmPasswordError => 'Please confirm your password';

  @override
  String get registerPasswordMismatch => 'Passwords do not match';

  @override
  String get registerReferralCodeLabel => 'Referral Code (optional)';

  @override
  String get registerReferralCodeHint => 'Enter referral code';

  @override
  String get registerReferralApplied => 'Applied!';

  @override
  String get registerReferralFromLink => 'Referral code applied from link';

  @override
  String get registerAgreePrefix => 'I agree to the ';

  @override
  String get registerTermsAndConditions => 'Terms & Conditions';

  @override
  String get registerAndSeparator => ' and ';

  @override
  String get registerAcceptTermsError => 'Please accept the Terms & Conditions';

  @override
  String get registerButton => 'Register';

  @override
  String get registerOrSeparator => 'OR';

  @override
  String get registerAlreadyHaveAccount => 'Already have an account? ';

  @override
  String get registerLoginLink => 'Login';

  @override
  String get telegramNotInstalledTitle => 'Telegram Not Installed';

  @override
  String get telegramNotInstalledMessage =>
      'The Telegram app is not installed on your device. You can install it from the app store or use the web version.';

  @override
  String get telegramUseWeb => 'Use Web';

  @override
  String get telegramInstall => 'Install';

  @override
  String get appLockTitle => 'CyberVPN Locked';

  @override
  String get appLockSubtitle => 'Authenticate to continue';

  @override
  String get appLockUnlockButton => 'Unlock';

  @override
  String appLockUnlockWithBiometric(String biometricLabel) {
    return 'Unlock with $biometricLabel';
  }

  @override
  String get appLockTooManyAttempts => 'Too many failed attempts';

  @override
  String get appLockUsePin => 'Use device PIN';

  @override
  String appLockTryAgain(String biometricLabel) {
    return 'Try $biometricLabel again';
  }

  @override
  String get appLockLocalizedReason => 'Unlock CyberVPN with your device PIN';

  @override
  String get biometricSettingsTitle => 'Security';

  @override
  String get biometricAuthSection => 'Biometric Authentication';

  @override
  String get biometricLoginLabel => 'Biometric Login';

  @override
  String get biometricLoginDescription => 'Use biometrics to sign in quickly';

  @override
  String get biometricLoginEnabled => 'Biometric login enabled';

  @override
  String get biometricLoginDisabled => 'Biometric login disabled';

  @override
  String get biometricVerificationRequired => 'Biometric verification required';

  @override
  String get biometricEnterCredentialsTitle => 'Enter credentials';

  @override
  String get biometricEnterCredentialsMessage =>
      'Enter your login credentials to enable quick sign-in with biometrics.';

  @override
  String get biometricSave => 'Save';

  @override
  String get biometricAppLockLabel => 'App Lock';

  @override
  String get biometricAppLockDescription =>
      'Require biometrics when returning to app (30+ seconds)';

  @override
  String get biometricAppLockEnabled => 'App lock enabled';

  @override
  String get biometricAppLockDisabled => 'App lock disabled';

  @override
  String get biometricUnavailableTitle => 'Biometrics Unavailable';

  @override
  String get biometricUnavailableMessage =>
      'Your device does not support biometric authentication, or no biometrics are enrolled.';

  @override
  String get biometricLoadingState => 'Loading...';

  @override
  String get biometricUnavailableState => 'Unavailable';

  @override
  String get biometricLabelFingerprint => 'Fingerprint';

  @override
  String get biometricLabelGeneric => 'Biometrics';

  @override
  String get biometricAvailableOnDevice => 'Available on this device';

  @override
  String get biometricSettingsChanged =>
      'Your biometric settings have changed. Please sign in with your password and re-enable biometric login in settings.';

  @override
  String get biometricPasswordChanged =>
      'Your password has changed. Please sign in with your password.';

  @override
  String get settingsNotificationPrefsTitle => 'Notification Preferences';

  @override
  String get settingsNotificationConnectionLabel => 'Connection Status';

  @override
  String get settingsNotificationConnectionDescription =>
      'Get notified when VPN connects or disconnects';

  @override
  String get settingsNotificationServerLabel => 'Server Changes';

  @override
  String get settingsNotificationServerDescription =>
      'Get notified when server is switched';

  @override
  String get settingsNotificationSubscriptionLabel => 'Subscription Alerts';

  @override
  String get settingsNotificationSubscriptionDescription =>
      'Get notified about subscription expiry';

  @override
  String get settingsNotificationSecurityLabel => 'Security Alerts';

  @override
  String get settingsNotificationSecurityDescription =>
      'Get notified about security events';

  @override
  String get settingsNotificationPromotionLabel => 'Promotions';

  @override
  String get settingsNotificationPromotionDescription =>
      'Receive promotional notifications';

  @override
  String get settingsNotificationUpdateLabel => 'System Updates';

  @override
  String get settingsNotificationUpdateDescription =>
      'Get notified about app updates';

  @override
  String get settingsVpnProtocolWireGuard => 'WireGuard';

  @override
  String get settingsVpnProtocolOpenVpn => 'OpenVPN';

  @override
  String get settingsVpnProtocolIkev2 => 'IKEv2';

  @override
  String get settingsVpnProtocolAuto => 'Auto';

  @override
  String get settingsThemeDark => 'Dark';

  @override
  String get settingsThemeLight => 'Light';

  @override
  String get settingsThemeSystem => 'System';

  @override
  String get settingsLanguageSearchHint => 'Search languages';

  @override
  String get settingsVersionInfo => 'Version Info';

  @override
  String get settingsPrivacyAndTerms => 'Privacy & Terms';

  @override
  String get settingsContactSupport => 'Contact Support';

  @override
  String settingsAppVersion(String version) {
    return 'App version $version';
  }

  @override
  String settingsBuildNumber(String build) {
    return 'Build $build';
  }

  @override
  String get settingsRateApp => 'Rate CyberVPN';

  @override
  String get settingsShareApp => 'Share with Friends';

  @override
  String get settingsDeleteData => 'Delete All Data';

  @override
  String get profileSaveButton => 'Save';

  @override
  String get profileSaveSuccess => 'Profile updated successfully';

  @override
  String get profileAvatarChange => 'Change Avatar';

  @override
  String get profileAvatarRemove => 'Remove Avatar';

  @override
  String get profilePasswordUpdated => 'Password updated successfully';

  @override
  String get profilePasswordRequirements =>
      'Password must be at least 8 characters with letters and numbers';

  @override
  String get profileAccountInfo => 'Account Information';

  @override
  String get profileSecuritySection => 'Security';

  @override
  String get profileDangerZone => 'Danger Zone';

  @override
  String get profileDeleteConfirmInput => 'Type DELETE to confirm';

  @override
  String get profileDeleteInProgress => 'Deleting account...';

  @override
  String get profileSessionInfo => 'Session Information';

  @override
  String profileLastLogin(String date) {
    return 'Last login: $date';
  }

  @override
  String profileCreatedAt(String date) {
    return 'Account created: $date';
  }

  @override
  String get configImportManualEntry => 'Manual Entry';

  @override
  String get configImportManualDescription =>
      'Enter VPN configuration details manually.';

  @override
  String get configImportServerAddress => 'Server Address';

  @override
  String get configImportServerPort => 'Port';

  @override
  String get configImportProtocol => 'Protocol';

  @override
  String get configImportPrivateKey => 'Private Key';

  @override
  String get configImportPublicKey => 'Public Key';

  @override
  String get configImportConfigName => 'Configuration Name';

  @override
  String get configImportConfigNameHint =>
      'Enter a name for this configuration';

  @override
  String get configImportSaving => 'Saving configuration...';

  @override
  String get configImportDeleteConfirm =>
      'Are you sure you want to delete this configuration?';

  @override
  String get configImportDeleteSuccess => 'Configuration deleted.';

  @override
  String get configImportNoConfigs => 'No imported configurations yet.';

  @override
  String get configImportManageTitle => 'Manage Configurations';

  @override
  String get configImportActiveLabel => 'Active';

  @override
  String get configImportConnectButton => 'Connect';

  @override
  String get configImportEditButton => 'Edit';

  @override
  String get configImportDeleteButton => 'Delete';

  @override
  String get subscriptionTitle => 'Subscription Plans';

  @override
  String get subscriptionCurrentPlan => 'Current Plan';

  @override
  String get subscriptionFreePlan => 'Free';

  @override
  String get subscriptionTrialPlan => 'Trial';

  @override
  String get subscriptionBasicPlan => 'Basic';

  @override
  String get subscriptionPremiumPlan => 'Premium';

  @override
  String get subscriptionMonthly => 'Monthly';

  @override
  String get subscriptionYearly => 'Yearly';

  @override
  String get subscriptionLifetime => 'Lifetime';

  @override
  String subscriptionPricePerMonth(String price) {
    return '$price/month';
  }

  @override
  String subscriptionPricePerYear(String price) {
    return '$price/year';
  }

  @override
  String subscriptionSavePercent(int percent) {
    return 'Save $percent%';
  }

  @override
  String get subscriptionSubscribeButton => 'Subscribe';

  @override
  String get subscriptionRestorePurchases => 'Restore Purchases';

  @override
  String get subscriptionRestoreSuccess => 'Purchases restored successfully';

  @override
  String get subscriptionRestoreNotFound => 'No previous purchases found';

  @override
  String get subscriptionCancelButton => 'Cancel Subscription';

  @override
  String get subscriptionCancelConfirm =>
      'Are you sure you want to cancel your subscription?';

  @override
  String get subscriptionCancelSuccess => 'Subscription cancelled';

  @override
  String get subscriptionRenewButton => 'Renew Subscription';

  @override
  String subscriptionExpiresOn(String date) {
    return 'Expires on $date';
  }

  @override
  String get subscriptionAutoRenew => 'Auto-renew enabled';

  @override
  String get subscriptionFeatureUnlimitedData => 'Unlimited data';

  @override
  String get subscriptionFeatureAllServers => 'Access to all servers';

  @override
  String get subscriptionFeatureNoAds => 'No ads';

  @override
  String get subscriptionFeaturePriority => 'Priority support';

  @override
  String subscriptionFeatureDevices(int count) {
    return 'Up to $count devices';
  }

  @override
  String subscriptionTrafficUsed(String used, String total) {
    return '$used of $total used';
  }

  @override
  String get subscriptionUpgradePrompt => 'Upgrade for more features';

  @override
  String get subscriptionProcessing => 'Processing payment...';

  @override
  String get subscriptionPaymentMethod => 'Payment Method';

  @override
  String get serverListTitle => 'Server List';

  @override
  String get serverListSearchHint => 'Search servers...';

  @override
  String get serverListFilterAll => 'All';

  @override
  String get serverListFilterFavorites => 'Favorites';

  @override
  String get serverListFilterRecommended => 'Recommended';

  @override
  String get serverListNoResults => 'No servers found';

  @override
  String serverListPing(int ping) {
    return '$ping ms';
  }

  @override
  String serverListLoad(int load) {
    return '$load% load';
  }

  @override
  String get serverListAddFavorite => 'Add to favorites';

  @override
  String get serverListRemoveFavorite => 'Remove from favorites';

  @override
  String serverListConnecting(String server) {
    return 'Connecting to $server...';
  }

  @override
  String get serverListSortBy => 'Sort by';

  @override
  String get serverListSortName => 'Name';

  @override
  String get serverListSortPing => 'Ping';

  @override
  String get serverListSortLoad => 'Load';

  @override
  String get notificationSettingsTitle => 'Notification Settings';

  @override
  String get notificationEnablePush => 'Enable Push Notifications';

  @override
  String get notificationEnablePushDescription =>
      'Receive important updates about your VPN connection';

  @override
  String get notificationSoundLabel => 'Notification Sound';

  @override
  String get notificationVibrationLabel => 'Vibration';

  @override
  String get notificationQuietHoursLabel => 'Quiet Hours';

  @override
  String get notificationQuietHoursDescription =>
      'Mute notifications during specified hours';

  @override
  String get diagnosticsNetworkCheck => 'Network Check';

  @override
  String get diagnosticsDnsCheck => 'DNS Resolution';

  @override
  String get diagnosticsLatencyCheck => 'Latency Check';

  @override
  String get diagnosticsFirewallCheck => 'Firewall Check';

  @override
  String get diagnosticsStatusPassed => 'Passed';

  @override
  String get diagnosticsStatusFailed => 'Failed';

  @override
  String get diagnosticsStatusRunning => 'Running...';

  @override
  String get diagnosticsRunAll => 'Run All Checks';

  @override
  String get diagnosticsShareResults => 'Share Results';

  @override
  String get commonSave => 'Save';

  @override
  String get commonDelete => 'Delete';

  @override
  String get commonEdit => 'Edit';

  @override
  String get commonClose => 'Close';

  @override
  String get commonBack => 'Back';

  @override
  String get commonNext => 'Next';

  @override
  String get commonDone => 'Done';

  @override
  String get commonSearch => 'Search';

  @override
  String get commonLoading => 'Loading...';

  @override
  String get commonNoData => 'No data available';

  @override
  String get commonRefresh => 'Refresh';

  @override
  String get commonCopy => 'Copy';

  @override
  String get commonCopied => 'Copied to clipboard';

  @override
  String get commonShare => 'Share';

  @override
  String get commonYes => 'Yes';

  @override
  String get commonNo => 'No';

  @override
  String get commonOk => 'OK';

  @override
  String get commonContinue => 'Continue';

  @override
  String get commonSkip => 'Skip';

  @override
  String get commonLearnMore => 'Learn More';

  @override
  String get errorNoConnection =>
      'No internet connection. Please check your network.';

  @override
  String get errorTimeout => 'Request timed out. Please try again.';

  @override
  String get errorGeneric => 'Something went wrong. Please try again.';

  @override
  String get errorLoadingData => 'Failed to load data.';

  @override
  String get errorSavingData => 'Failed to save data.';

  @override
  String get errorSessionInvalid =>
      'Your session is invalid. Please log in again.';

  @override
  String get a11yShowPassword => 'Show password';

  @override
  String get a11yHidePassword => 'Hide password';

  @override
  String a11yServerPing(int ping) {
    return 'Server ping: $ping milliseconds';
  }

  @override
  String a11yServerLoad(int load) {
    return 'Server load: $load percent';
  }

  @override
  String get a11yFavoriteServer => 'Favorite server';

  @override
  String get a11yRemoveFavorite => 'Remove from favorites';

  @override
  String get a11ySubscriptionActive => 'Active subscription';

  @override
  String get a11ySubscriptionExpired => 'Expired subscription';

  @override
  String get a11yBiometricLogin => 'Biometric login toggle';

  @override
  String get a11yAppLockToggle => 'App lock toggle';

  @override
  String get a11yProtocolSelect => 'Select VPN protocol';

  @override
  String get a11yThemeSelect => 'Select theme mode';

  @override
  String get a11yLanguageSelect => 'Select language';

  @override
  String a11yNotificationToggle(String type) {
    return 'Toggle notification for $type';
  }

  @override
  String get a11ySpeedTestProgress => 'Speed test in progress';

  @override
  String get a11yDiagnosticsProgress => 'Diagnostics in progress';

  @override
  String a11yTrafficUsage(int percent) {
    return 'Traffic usage: $percent percent';
  }

  @override
  String a11yConnectionDuration(String duration) {
    return 'Connected for $duration';
  }

  @override
  String get quickSetupTitle => 'Quick Setup';

  @override
  String get quickSetupWelcome => 'Let\'s get you connected';

  @override
  String get quickSetupSelectServer => 'Select a server to get started';

  @override
  String get quickSetupRecommended => 'Recommended for you';

  @override
  String get quickSetupConnectButton => 'Connect Now';

  @override
  String get quickSetupSkip => 'Skip for now';

  @override
  String get quickSetupComplete => 'You\'re all set!';

  @override
  String get splashLoading => 'Loading...';

  @override
  String get splashInitializing => 'Initializing...';
}
