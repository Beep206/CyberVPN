// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Persian (`fa`).
class AppLocalizationsFa extends AppLocalizations {
  AppLocalizationsFa([String locale = 'fa']) : super(locale);

  @override
  String get appName => 'CyberVPN';

  @override
  String get login => 'ورود';

  @override
  String get register => 'ثبت‌نام';

  @override
  String get email => 'ایمیل';

  @override
  String get password => 'رمز عبور';

  @override
  String get confirmPassword => 'تأیید رمز عبور';

  @override
  String get forgotPassword => 'رمز عبور را فراموش کردید؟';

  @override
  String get orContinueWith => 'یا ادامه با';

  @override
  String get connect => 'اتصال';

  @override
  String get disconnect => 'قطع اتصال';

  @override
  String get connecting => 'در حال اتصال...';

  @override
  String get disconnecting => 'در حال قطع اتصال...';

  @override
  String get connected => 'متصل';

  @override
  String get disconnected => 'قطع شده';

  @override
  String get servers => 'سرورها';

  @override
  String get subscription => 'اشتراک';

  @override
  String get settings => 'تنظیمات';

  @override
  String get profile => 'پروفایل';

  @override
  String get selectServer => 'انتخاب سرور';

  @override
  String get autoSelect => 'انتخاب خودکار';

  @override
  String get fastestServer => 'سریع‌ترین سرور';

  @override
  String get nearestServer => 'نزدیک‌ترین سرور';

  @override
  String get killSwitch => 'کلید قطع';

  @override
  String get splitTunneling => 'تونل تقسیم‌شده';

  @override
  String get autoConnect => 'اتصال خودکار';

  @override
  String get language => 'زبان';

  @override
  String get theme => 'پوسته';

  @override
  String get darkMode => 'حالت تاریک';

  @override
  String get lightMode => 'حالت روشن';

  @override
  String get systemDefault => 'پیش‌فرض سیستم';

  @override
  String get logout => 'خروج';

  @override
  String get logoutConfirm => 'آیا مطمئن هستید که می‌خواهید خارج شوید؟';

  @override
  String get cancel => 'لغو';

  @override
  String get confirm => 'تأیید';

  @override
  String get retry => 'تلاش مجدد';

  @override
  String get errorOccurred => 'خطایی رخ داد';

  @override
  String get noInternet => 'اتصال اینترنتی وجود ندارد';

  @override
  String get downloadSpeed => 'دانلود';

  @override
  String get uploadSpeed => 'آپلود';

  @override
  String get connectionTime => 'زمان اتصال';

  @override
  String get dataUsed => 'داده مصرف‌شده';

  @override
  String get currentPlan => 'طرح فعلی';

  @override
  String get upgradePlan => 'ارتقای طرح';

  @override
  String daysRemaining(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count روز باقی‌مانده',
      one: 'یک روز باقی‌مانده',
    );
    return '$_temp0';
  }

  @override
  String get referral => 'معرفی';

  @override
  String get shareReferralCode => 'اشتراک‌گذاری کد معرفی';

  @override
  String get support => 'پشتیبانی';

  @override
  String get privacyPolicy => 'سیاست حریم خصوصی';

  @override
  String get termsOfService => 'شرایط خدمات';

  @override
  String version(String version) {
    return 'نسخه $version';
  }

  @override
  String get onboardingWelcomeTitle => 'به CyberVPN خوش آمدید';

  @override
  String get onboardingWelcomeDescription =>
      'دسترسی امن، سریع و خصوصی به اینترنت در دسترس شما.';

  @override
  String get onboardingFeaturesTitle => 'ویژگی‌های قدرتمند';

  @override
  String get onboardingFeaturesDescription =>
      'کلید قطع، تونل تقسیم‌شده و رمزگذاری نظامی برای حفظ امنیت شما.';

  @override
  String get onboardingPrivacyTitle => 'حریم خصوصی شما مهم است';

  @override
  String get onboardingPrivacyDescription =>
      'سیاست عدم ذخیره گزارش‌ها. ما هرگز داده‌های مرور شما را ردیابی، ذخیره یا به اشتراک نمی‌گذاریم.';

  @override
  String get onboardingSpeedTitle => 'سرعت برق‌آسا';

  @override
  String get onboardingSpeedDescription =>
      'به سرورهای بهینه‌شده در سراسر جهان متصل شوید برای بهترین سرعت‌ها.';

  @override
  String get onboardingSkip => 'رد شدن';

  @override
  String get onboardingNext => 'بعدی';

  @override
  String get onboardingGetStarted => 'شروع کنید';

  @override
  String get onboardingBack => 'بازگشت';

  @override
  String onboardingPageIndicator(int current, int total) {
    return 'صفحه $current از $total';
  }

  @override
  String get settingsTitle => 'تنظیمات';

  @override
  String get settingsGeneral => 'عمومی';

  @override
  String get settingsVpn => 'تنظیمات VPN';

  @override
  String get settingsAppearance => 'ظاهر';

  @override
  String get settingsDebug => 'اشکال‌زدایی';

  @override
  String get settingsNotifications => 'اعلان‌ها';

  @override
  String get settingsAbout => 'درباره';

  @override
  String get settingsVpnProtocolLabel => 'پروتکل';

  @override
  String get settingsVpnProtocolDescription =>
      'پروتکل VPN مورد استفاده برای اتصالات را انتخاب کنید.';

  @override
  String get settingsAutoConnectLabel => 'اتصال خودکار';

  @override
  String get settingsAutoConnectDescription =>
      'هنگام شروع برنامه به طور خودکار متصل شوید.';

  @override
  String get settingsKillSwitchLabel => 'کلید قطع';

  @override
  String get settingsKillSwitchDescription =>
      'اینترنت را در صورت قطع اتصال VPN مسدود کنید.';

  @override
  String get settingsDnsLabel => 'DNS سفارشی';

  @override
  String get settingsDnsDescription =>
      'از سرور DNS سفارشی برای تفکیک استفاده کنید.';

  @override
  String get settingsDnsPlaceholder => 'آدرس DNS را وارد کنید';

  @override
  String get settingsSplitTunnelingLabel => 'تونل تقسیم‌شده';

  @override
  String get settingsSplitTunnelingDescription =>
      'انتخاب کنید کدام برنامه‌ها از اتصال VPN استفاده کنند.';

  @override
  String get settingsThemeModeLabel => 'حالت پوسته';

  @override
  String get settingsThemeModeDescription =>
      'بین پوسته روشن، تاریک یا سیستم انتخاب کنید.';

  @override
  String get settingsLanguageLabel => 'زبان';

  @override
  String get settingsLanguageDescription => 'زبان مورد نظر خود را انتخاب کنید.';

  @override
  String get settingsDebugLogsLabel => 'گزارش‌های اشکال‌زدایی';

  @override
  String get settingsDebugLogsDescription =>
      'فعال‌سازی گزارش‌گیری دقیق برای عیب‌یابی.';

  @override
  String get settingsExportLogsLabel => 'خروجی گزارش‌ها';

  @override
  String get settingsExportLogsDescription =>
      'خروجی گزارش‌های اشکال‌زدایی برای پشتیبانی.';

  @override
  String get settingsResetLabel => 'بازنشانی تنظیمات';

  @override
  String get settingsResetDescription =>
      'بازگردانی همه تنظیمات به مقادیر پیش‌فرض.';

  @override
  String get settingsResetConfirm =>
      'آیا مطمئن هستید که می‌خواهید همه تنظیمات را بازنشانی کنید؟';

  @override
  String get settingsStartOnBootLabel => 'شروع در بوت';

  @override
  String get settingsStartOnBootDescription =>
      'CyberVPN را هنگام روشن شدن دستگاه به طور خودکار اجرا کنید.';

  @override
  String get settingsConnectionTimeoutLabel => 'مهلت اتصال';

  @override
  String get settingsConnectionTimeoutDescription =>
      'حداکثر زمان انتظار قبل از لغو تلاش اتصال.';

  @override
  String settingsConnectionTimeoutSeconds(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count ثانیه',
      one: 'یک ثانیه',
    );
    return '$_temp0';
  }

  @override
  String get profileDashboard => 'داشبورد پروفایل';

  @override
  String get profileEditProfile => 'ویرایش پروفایل';

  @override
  String get profileDisplayName => 'نام نمایشی';

  @override
  String get profileEmailAddress => 'آدرس ایمیل';

  @override
  String get profileChangePassword => 'تغییر رمز عبور';

  @override
  String get profileCurrentPassword => 'رمز عبور فعلی';

  @override
  String get profileNewPassword => 'رمز عبور جدید';

  @override
  String get profileConfirmNewPassword => 'تأیید رمز عبور جدید';

  @override
  String get profileTwoFactorAuth => 'احراز هویت دومرحله‌ای';

  @override
  String get profileTwoFactorAuthDescription =>
      'یک لایه امنیتی اضافی به حساب خود اضافه کنید.';

  @override
  String get profileTwoFactorEnable => 'فعال‌سازی احراز هویت دومرحله‌ای';

  @override
  String get profileTwoFactorDisable => 'غیرفعال‌سازی احراز هویت دومرحله‌ای';

  @override
  String get profileTwoFactorSetup => 'راه‌اندازی احراز هویت دومرحله‌ای';

  @override
  String get profileTwoFactorScanQr =>
      'این کد QR را با برنامه احراز هویت خود اسکن کنید.';

  @override
  String get profileTwoFactorEnterCode =>
      'کد 6 رقمی را از برنامه احراز هویت خود وارد کنید.';

  @override
  String get profileTwoFactorBackupCodes => 'کدهای پشتیبان';

  @override
  String get profileTwoFactorBackupCodesDescription =>
      'این کدها را در مکانی امن ذخیره کنید. اگر دسترسی به برنامه احراز هویت را از دست دادید، می‌توانید از آنها برای ورود استفاده کنید.';

  @override
  String get profileOauthAccounts => 'حساب‌های متصل';

  @override
  String get profileOauthAccountsDescription =>
      'حساب‌های اجتماعی متصل خود را مدیریت کنید.';

  @override
  String get profileOauthLink => 'اتصال حساب';

  @override
  String get profileOauthUnlink => 'قطع اتصال';

  @override
  String get profileOauthUnlinkConfirm =>
      'آیا مطمئن هستید که می‌خواهید اتصال این حساب را قطع کنید؟';

  @override
  String get profileTrustedDevices => 'دستگاه‌های مورد اعتماد';

  @override
  String get profileTrustedDevicesDescription =>
      'دستگاه‌هایی که می‌توانند به حساب شما دسترسی داشته باشند را مدیریت کنید.';

  @override
  String get profileDeviceCurrent => 'دستگاه فعلی';

  @override
  String profileDeviceLastActive(String date) {
    return 'آخرین فعالیت $date';
  }

  @override
  String get profileDeviceRevoke => 'لغو دسترسی';

  @override
  String get profileDeviceRevokeConfirm =>
      'آیا مطمئن هستید که می‌خواهید دسترسی این دستگاه را لغو کنید؟';

  @override
  String get profileDeviceRevokeAll => 'لغو دسترسی همه دستگاه‌ها';

  @override
  String get profileDeleteAccount => 'حذف حساب';

  @override
  String get profileDeleteAccountDescription =>
      'حساب و تمام داده‌های مرتبط را برای همیشه حذف کنید.';

  @override
  String get profileDeleteAccountConfirm =>
      'آیا مطمئن هستید که می‌خواهید حساب خود را حذف کنید؟ این عمل قابل بازگشت نیست.';

  @override
  String get profileDeleteAccountButton => 'حذف حساب من';

  @override
  String get profileSubscriptionStatus => 'وضعیت اشتراک';

  @override
  String profileMemberSince(String date) {
    return 'عضو از $date';
  }

  @override
  String get configImportTitle => 'واردکردن تنظیمات';

  @override
  String get configImportQrScanTitle => 'اسکن کد QR';

  @override
  String get configImportQrScanDescription =>
      'دوربین را به سمت کد QR تنظیمات VPN بگیرید.';

  @override
  String get configImportScanQrButton => 'اسکن کد QR';

  @override
  String get configImportFromClipboard => 'واردکردن از کلیپبورد';

  @override
  String get configImportFromClipboardDescription =>
      'یک لینک یا متن تنظیمات را از کلیپبورد جایگذاری کنید.';

  @override
  String get configImportFromFile => 'واردکردن از فایل';

  @override
  String get configImportFromFileDescription =>
      'یک فایل تنظیمات را از دستگاه خود انتخاب کنید.';

  @override
  String get configImportPreviewTitle => 'پیش‌نمایش تنظیمات';

  @override
  String get configImportPreviewServer => 'سرور';

  @override
  String get configImportPreviewProtocol => 'پروتکل';

  @override
  String get configImportPreviewPort => 'پورت';

  @override
  String get configImportConfirmButton => 'واردکردن تنظیمات';

  @override
  String get configImportCancelButton => 'لغو واردکردن';

  @override
  String get configImportSuccess => 'تنظیمات با موفقیت وارد شد.';

  @override
  String get configImportError => 'واردکردن تنظیمات ناموفق بود.';

  @override
  String get configImportInvalidFormat => 'فرمت تنظیمات نامعتبر است.';

  @override
  String get configImportDuplicate => 'این تنظیمات قبلاً وجود دارد.';

  @override
  String get configImportCameraPermission =>
      'برای اسکن کدهای QR به مجوز دوربین نیاز است.';

  @override
  String get notificationCenterTitle => 'اعلان‌ها';

  @override
  String get notificationCenterEmpty => 'هنوز اعلانی وجود ندارد.';

  @override
  String get notificationCenterMarkAllRead =>
      'علامت‌گذاری همه به عنوان خوانده‌شده';

  @override
  String get notificationCenterClearAll => 'پاک کردن همه';

  @override
  String get notificationTypeConnectionStatus => 'وضعیت اتصال';

  @override
  String get notificationTypeServerSwitch => 'تغییر سرور';

  @override
  String get notificationTypeSubscriptionExpiry => 'انقضای اشتراک';

  @override
  String get notificationTypeSecurityAlert => 'هشدار امنیتی';

  @override
  String get notificationTypePromotion => 'تبلیغات';

  @override
  String get notificationTypeSystemUpdate => 'به‌روزرسانی سیستم';

  @override
  String notificationConnected(String serverName) {
    return 'متصل به $serverName';
  }

  @override
  String get notificationDisconnected => 'اتصال VPN قطع شد.';

  @override
  String notificationServerSwitched(String serverName) {
    return 'به $serverName تغییر یافت.';
  }

  @override
  String notificationSubscriptionExpiring(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'اشتراک شما تا $count روز دیگر منقضی می‌شود',
      one: 'اشتراک شما تا یک روز دیگر منقضی می‌شود',
    );
    return '$_temp0.';
  }

  @override
  String get notificationSubscriptionExpired =>
      'اشتراک شما منقضی شده است. برای ادامه استفاده از CyberVPN تمدید کنید.';

  @override
  String notificationUnreadCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count اعلان خوانده‌نشده',
      one: 'یک اعلان خوانده‌نشده',
    );
    return '$_temp0';
  }

  @override
  String get referralDashboardTitle => 'برنامه معرفی';

  @override
  String get referralDashboardDescription =>
      'دوستان خود را دعوت کنید و پاداش بگیرید.';

  @override
  String get referralShareLink => 'اشتراک‌گذاری لینک معرفی';

  @override
  String get referralCopyLink => 'کپی لینک';

  @override
  String get referralLinkCopied => 'لینک معرفی در کلیپبورد کپی شد.';

  @override
  String get referralCodeLabel => 'کد معرفی شما';

  @override
  String referralRewardsEarned(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count پاداش کسب شده',
      one: 'یک پاداش کسب شده',
    );
    return '$_temp0';
  }

  @override
  String referralFriendsInvited(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count دوست دعوت شده',
      one: 'یک دوست دعوت شده',
    );
    return '$_temp0';
  }

  @override
  String referralRewardDescription(int days) {
    return 'برای هر دوستی که اشتراک می‌گیرد $days روز رایگان دریافت کنید.';
  }

  @override
  String get referralHistory => 'تاریخچه معرفی';

  @override
  String get referralPending => 'در انتظار';

  @override
  String get referralCompleted => 'تکمیل شده';

  @override
  String get referralExpired => 'منقضی شده';

  @override
  String get diagnosticsTitle => 'عیب‌یابی';

  @override
  String get diagnosticsDescription =>
      'اتصال خود را آزمایش کنید و مشکلات را برطرف کنید.';

  @override
  String get speedTestTitle => 'تست سرعت';

  @override
  String get speedTestStart => 'شروع تست سرعت';

  @override
  String get speedTestRunning => 'در حال تست...';

  @override
  String get speedTestDownloadSpeed => 'سرعت دانلود';

  @override
  String get speedTestUploadSpeed => 'سرعت آپلود';

  @override
  String get speedTestPing => 'پینگ';

  @override
  String speedTestPingMs(int value) {
    return '$value میلی‌ثانیه';
  }

  @override
  String speedTestMbps(String value) {
    return '$value مگابیت بر ثانیه';
  }

  @override
  String get speedTestResult => 'نتیجه تست سرعت';

  @override
  String get speedTestHistory => 'تاریخچه تست سرعت';

  @override
  String get speedTestStepConnecting => 'در حال اتصال به سرور تست...';

  @override
  String get speedTestStepDownload => 'در حال تست سرعت دانلود...';

  @override
  String get speedTestStepUpload => 'در حال تست سرعت آپلود...';

  @override
  String get speedTestStepPing => 'در حال اندازه‌گیری تأخیر...';

  @override
  String get speedTestStepComplete => 'تست کامل شد.';

  @override
  String get speedTestNoVpn => 'قبل از اجرای تست سرعت به VPN متصل شوید.';

  @override
  String get logViewerTitle => 'نمایشگر گزارش‌ها';

  @override
  String get logViewerEmpty => 'گزارشی موجود نیست.';

  @override
  String get logViewerExportButton => 'خروجی گزارش‌ها';

  @override
  String get logViewerClearButton => 'پاک کردن گزارش‌ها';

  @override
  String get logViewerClearConfirm =>
      'آیا مطمئن هستید که می‌خواهید همه گزارش‌ها را پاک کنید؟';

  @override
  String get logViewerFilterLabel => 'فیلتر';

  @override
  String get logViewerFilterAll => 'همه';

  @override
  String get logViewerFilterError => 'خطاها';

  @override
  String get logViewerFilterWarning => 'هشدارها';

  @override
  String get logViewerFilterInfo => 'اطلاعات';

  @override
  String get logViewerCopied => 'ورودی گزارش در کلیپبورد کپی شد.';

  @override
  String get logViewerExportSuccess => 'گزارش‌ها با موفقیت خروجی شدند.';

  @override
  String get logViewerExportError => 'خروجی گزارش‌ها ناموفق بود.';

  @override
  String get widgetConnectLabel => 'اتصال به VPN';

  @override
  String get widgetDisconnectLabel => 'قطع VPN';

  @override
  String get widgetStatusLabel => 'وضعیت VPN';

  @override
  String get widgetServerLabel => 'سرور فعلی';

  @override
  String get quickActionConnect => 'اتصال';

  @override
  String get quickActionDisconnect => 'قطع';

  @override
  String get quickActionServers => 'سرورها';

  @override
  String get quickActionSpeedTest => 'تست سرعت';

  @override
  String get quickActionSettings => 'تنظیمات';

  @override
  String get quickActionSupport => 'پشتیبانی';

  @override
  String get errorConnectionFailed =>
      'اتصال ناموفق بود. لطفاً دوباره تلاش کنید.';

  @override
  String get errorConnectionTimeout =>
      'مهلت اتصال تمام شد. اتصال اینترنتی خود را بررسی کنید.';

  @override
  String get errorServerUnavailable =>
      'سرور در حال حاضر در دسترس نیست. سرور دیگری را امتحان کنید.';

  @override
  String get errorInvalidConfig =>
      'تنظیمات نامعتبر است. لطفاً تنظیمات خود را دوباره وارد کنید.';

  @override
  String get errorSubscriptionExpired =>
      'اشتراک شما منقضی شده است. لطفاً برای ادامه تمدید کنید.';

  @override
  String get errorSubscriptionRequired =>
      'برای استفاده از این ویژگی به اشتراک نیاز است.';

  @override
  String get errorAuthenticationFailed =>
      'احراز هویت ناموفق بود. لطفاً دوباره وارد شوید.';

  @override
  String get errorTokenExpired => 'نشست منقضی شده است. لطفاً دوباره وارد شوید.';

  @override
  String get errorNetworkUnreachable =>
      'شبکه در دسترس نیست. اتصال خود را بررسی کنید.';

  @override
  String get errorPermissionDenied => 'دسترسی رد شد.';

  @override
  String get errorRateLimited => 'درخواست‌های زیادی. لطفاً لحظه‌ای صبر کنید.';

  @override
  String get errorUnexpected =>
      'خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره تلاش کنید.';

  @override
  String get errorServerError => 'خطای سرور. لطفاً بعداً تلاش کنید.';

  @override
  String get errorInvalidCredentials => 'ایمیل یا رمز عبور نامعتبر است.';

  @override
  String get errorAccountLocked =>
      'حساب شما قفل شده است. لطفاً با پشتیبانی تماس بگیرید.';

  @override
  String get errorWeakPassword =>
      'رمز عبور بسیار ضعیف است. حداقل 8 کاراکتر با حروف و اعداد استفاده کنید.';

  @override
  String get errorEmailAlreadyInUse => 'این ایمیل قبلاً ثبت شده است.';

  @override
  String get errorInvalidEmail => 'لطفاً یک آدرس ایمیل معتبر وارد کنید.';

  @override
  String get errorFieldRequired => 'این فیلد الزامی است.';

  @override
  String get errorPaymentFailed =>
      'پرداخت ناموفق بود. دوباره تلاش کنید یا روش دیگری استفاده کنید.';

  @override
  String get errorQrScanFailed =>
      'اسکن کد QR ناموفق بود. لطفاً دوباره تلاش کنید.';

  @override
  String get a11yConnectButton => 'اتصال به سرور VPN';

  @override
  String get a11yDisconnectButton => 'قطع اتصال از سرور VPN';

  @override
  String get a11yServerStatusOnline => 'سرور آنلاین است';

  @override
  String get a11yServerStatusOffline => 'سرور آفلاین است';

  @override
  String get a11yServerStatusMaintenance => 'سرور در حال تعمیر و نگهداری است';

  @override
  String a11ySpeedIndicator(String speed) {
    return 'سرعت فعلی: $speed';
  }

  @override
  String a11yConnectionStatus(String status) {
    return 'وضعیت اتصال: $status';
  }

  @override
  String a11yServerSelect(String name, String country) {
    return 'انتخاب سرور $name در $country';
  }

  @override
  String get a11yNavigationMenu => 'منوی ناوبری';

  @override
  String get a11yCloseDialog => 'بستن پنجره';

  @override
  String a11yToggleSwitch(String label) {
    return 'تغییر $label';
  }

  @override
  String a11yNotificationBadge(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count اعلان',
      one: 'یک اعلان',
    );
    return '$_temp0';
  }

  @override
  String get a11yLoadingIndicator => 'در حال بارگذاری';

  @override
  String get a11yRefreshContent => 'بازآوری محتوا';

  @override
  String get a11yBackButton => 'بازگشت';

  @override
  String get a11ySearchField => 'جستجو';

  @override
  String get rootDetectionDialogTitle => 'Rooted/Jailbroken Device Detected';

  @override
  String get rootDetectionDialogDescription =>
      'Your device appears to be rooted (Android) or jailbroken (iOS). While CyberVPN will continue to work, please note that using a rooted/jailbroken device may expose you to security risks.\n\nWe understand that users in censored regions often rely on rooted devices for additional privacy tools. CyberVPN will not block your access, but we recommend being cautious about the apps you install and the permissions you grant.';

  @override
  String get rootDetectionDialogDismiss => 'I Understand';
}
