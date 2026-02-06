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
  String get errorTelegramAuthCancelled => 'Telegram login was cancelled.';

  @override
  String get errorTelegramAuthFailed =>
      'Telegram authentication failed. Please try again.';

  @override
  String get errorTelegramAuthExpired =>
      'Telegram login expired. Please try again.';

  @override
  String get errorTelegramNotInstalled =>
      'Telegram is not installed on this device.';

  @override
  String get errorTelegramAuthInvalid =>
      'Invalid Telegram authentication data.';

  @override
  String get errorBiometricUnavailable =>
      'Biometric authentication is not available on this device.';

  @override
  String get errorBiometricNotEnrolled =>
      'No biometric data enrolled. Please set up fingerprint or face recognition in device settings.';

  @override
  String get errorBiometricFailed =>
      'Biometric authentication failed. Please try again.';

  @override
  String get errorBiometricLocked =>
      'Biometric authentication is locked. Try again later or use your password.';

  @override
  String get errorSessionExpired =>
      'Your session has expired. Please log in again.';

  @override
  String get errorAccountDisabled =>
      'Your account has been disabled. Please contact support.';

  @override
  String errorRateLimitedWithCountdown(int seconds) {
    String _temp0 = intl.Intl.pluralLogic(
      seconds,
      locale: localeName,
      other: '$seconds seconds',
      one: '1 second',
    );
    return 'Too many attempts. Please try again in $_temp0.';
  }

  @override
  String get errorOfflineLoginRequired =>
      'You need to be online to log in. Please check your connection.';

  @override
  String get errorOfflineSessionExpired =>
      'Your cached session has expired. Please connect to the internet to log in.';

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

  @override
  String get rootDetectionBannerWarning =>
      'This device is rooted/jailbroken. Your connection may be less secure.';

  @override
  String get rootDetectionBannerBlocking =>
      'VPN is unavailable on rooted/jailbroken devices.';

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
