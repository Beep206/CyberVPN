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
      one: 'Остался 1 день',
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
      one: '1 секунда',
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
      one: '1 день',
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
      one: '1 непрочитанное уведомление',
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
      one: '1 награда получена',
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
      one: '1 друг приглашён',
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
      one: '1 уведомление',
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
}
