// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr([String locale = 'ar']) : super(locale);

  @override
  String get appName => 'CyberVPN';

  @override
  String get login => 'تسجيل الدخول';

  @override
  String get register => 'إنشاء حساب';

  @override
  String get email => 'البريد الإلكتروني';

  @override
  String get password => 'كلمة المرور';

  @override
  String get confirmPassword => 'تأكيد كلمة المرور';

  @override
  String get forgotPassword => 'نسيت كلمة المرور؟';

  @override
  String get orContinueWith => 'أو تابع باستخدام';

  @override
  String get connect => 'اتصال';

  @override
  String get disconnect => 'قطع الاتصال';

  @override
  String get connecting => 'جارٍ الاتصال...';

  @override
  String get disconnecting => 'جارٍ قطع الاتصال...';

  @override
  String get connected => 'متصل';

  @override
  String get disconnected => 'غير متصل';

  @override
  String get servers => 'الخوادم';

  @override
  String get subscription => 'الاشتراك';

  @override
  String get settings => 'الإعدادات';

  @override
  String get profile => 'الملف الشخصي';

  @override
  String get selectServer => 'اختر خادماً';

  @override
  String get autoSelect => 'اختيار تلقائي';

  @override
  String get fastestServer => 'أسرع خادم';

  @override
  String get nearestServer => 'أقرب خادم';

  @override
  String get killSwitch => 'مفتاح الإيقاف';

  @override
  String get splitTunneling => 'النفق المقسّم';

  @override
  String get autoConnect => 'اتصال تلقائي';

  @override
  String get language => 'اللغة';

  @override
  String get theme => 'المظهر';

  @override
  String get darkMode => 'الوضع الداكن';

  @override
  String get lightMode => 'الوضع الفاتح';

  @override
  String get systemDefault => 'إعداد النظام';

  @override
  String get logout => 'تسجيل الخروج';

  @override
  String get logoutConfirm => 'هل أنت متأكد أنك تريد تسجيل الخروج؟';

  @override
  String get cancel => 'إلغاء';

  @override
  String get confirm => 'تأكيد';

  @override
  String get retry => 'إعادة المحاولة';

  @override
  String get errorOccurred => 'حدث خطأ';

  @override
  String get noInternet => 'لا يوجد اتصال بالإنترنت';

  @override
  String get downloadSpeed => 'التنزيل';

  @override
  String get uploadSpeed => 'الرفع';

  @override
  String get connectionTime => 'وقت الاتصال';

  @override
  String get dataUsed => 'البيانات المستخدمة';

  @override
  String get currentPlan => 'الخطة الحالية';

  @override
  String get upgradePlan => 'ترقية الخطة';

  @override
  String daysRemaining(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count يوم متبقٍ',
      many: '$count يومًا متبقيًا',
      few: '$count أيام متبقية',
      two: 'يومان متبقيان',
      one: 'يوم واحد متبقٍ',
      zero: 'لا أيام متبقية',
    );
    return '$_temp0';
  }

  @override
  String get referral => 'الإحالة';

  @override
  String get shareReferralCode => 'مشاركة رمز الإحالة';

  @override
  String get support => 'الدعم';

  @override
  String get privacyPolicy => 'سياسة الخصوصية';

  @override
  String get termsOfService => 'شروط الخدمة';

  @override
  String version(String version) {
    return 'الإصدار $version';
  }

  @override
  String get onboardingWelcomeTitle => 'مرحبًا بك في CyberVPN';

  @override
  String get onboardingWelcomeDescription =>
      'وصول آمن وسريع وخاص إلى الإنترنت في متناول يدك.';

  @override
  String get onboardingFeaturesTitle => 'ميزات قوية';

  @override
  String get onboardingFeaturesDescription =>
      'مفتاح إيقاف، نفق مقسّم، وتشفير بمستوى عسكري للحفاظ على أمانك.';

  @override
  String get onboardingPrivacyTitle => 'خصوصيتك مهمة';

  @override
  String get onboardingPrivacyDescription =>
      'سياسة عدم الاحتفاظ بالسجلات. لا نتتبع أو نخزّن أو نشارك بيانات تصفحك أبدًا.';

  @override
  String get onboardingSpeedTitle => 'سريع كالبرق';

  @override
  String get onboardingSpeedDescription =>
      'اتصل بخوادم محسّنة حول العالم للحصول على أفضل السرعات.';

  @override
  String get onboardingSkip => 'تخطي';

  @override
  String get onboardingNext => 'التالي';

  @override
  String get onboardingGetStarted => 'ابدأ الآن';

  @override
  String get onboardingBack => 'رجوع';

  @override
  String onboardingPageIndicator(int current, int total) {
    return 'الصفحة $current من $total';
  }

  @override
  String get settingsTitle => 'الإعدادات';

  @override
  String get settingsGeneral => 'عام';

  @override
  String get settingsVpn => 'إعدادات VPN';

  @override
  String get settingsAppearance => 'المظهر';

  @override
  String get settingsDebug => 'التصحيح';

  @override
  String get settingsNotifications => 'الإشعارات';

  @override
  String get settingsAbout => 'حول';

  @override
  String get settingsVpnProtocolLabel => 'البروتوكول';

  @override
  String get settingsVpnProtocolDescription =>
      'حدد بروتوكول VPN المستخدم للاتصالات.';

  @override
  String get settingsAutoConnectLabel => 'اتصال تلقائي';

  @override
  String get settingsAutoConnectDescription =>
      'الاتصال تلقائيًا عند بدء التطبيق.';

  @override
  String get settingsKillSwitchLabel => 'مفتاح الإيقاف';

  @override
  String get settingsKillSwitchDescription =>
      'حظر الإنترنت إذا انقطع اتصال VPN.';

  @override
  String get settingsDnsLabel => 'DNS مخصص';

  @override
  String get settingsDnsDescription => 'استخدم خادم DNS مخصص للتحليل.';

  @override
  String get settingsDnsPlaceholder => 'أدخل عنوان DNS';

  @override
  String get settingsSplitTunnelingLabel => 'النفق المقسّم';

  @override
  String get settingsSplitTunnelingDescription =>
      'اختر التطبيقات التي تستخدم اتصال VPN.';

  @override
  String get settingsThemeModeLabel => 'وضع المظهر';

  @override
  String get settingsThemeModeDescription =>
      'اختر بين المظهر الفاتح أو الداكن أو مظهر النظام.';

  @override
  String get settingsLanguageLabel => 'اللغة';

  @override
  String get settingsLanguageDescription => 'حدد لغتك المفضلة.';

  @override
  String get settingsDebugLogsLabel => 'سجلات التصحيح';

  @override
  String get settingsDebugLogsDescription =>
      'تفعيل التسجيل المفصل لاستكشاف الأخطاء.';

  @override
  String get settingsExportLogsLabel => 'تصدير السجلات';

  @override
  String get settingsExportLogsDescription => 'تصدير سجلات التصحيح للدعم.';

  @override
  String get settingsResetLabel => 'إعادة تعيين الإعدادات';

  @override
  String get settingsResetDescription =>
      'استعادة جميع الإعدادات إلى القيم الافتراضية.';

  @override
  String get settingsResetConfirm =>
      'هل أنت متأكد أنك تريد إعادة تعيين جميع الإعدادات إلى الافتراضية؟';

  @override
  String get settingsStartOnBootLabel => 'البدء عند التشغيل';

  @override
  String get settingsStartOnBootDescription =>
      'تشغيل CyberVPN تلقائيًا عند بدء تشغيل جهازك.';

  @override
  String get settingsConnectionTimeoutLabel => 'مهلة الاتصال';

  @override
  String get settingsConnectionTimeoutDescription =>
      'الحد الأقصى للوقت قبل إلغاء محاولة الاتصال.';

  @override
  String settingsConnectionTimeoutSeconds(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count ثانية',
      many: '$count ثانيةً',
      few: '$count ثوانٍ',
      two: 'ثانيتان',
      one: 'ثانية واحدة',
      zero: 'لا ثوانٍ',
    );
    return '$_temp0';
  }

  @override
  String get profileDashboard => 'لوحة الملف الشخصي';

  @override
  String get profileEditProfile => 'تعديل الملف الشخصي';

  @override
  String get profileDisplayName => 'اسم العرض';

  @override
  String get profileEmailAddress => 'عنوان البريد الإلكتروني';

  @override
  String get profileChangePassword => 'تغيير كلمة المرور';

  @override
  String get profileCurrentPassword => 'كلمة المرور الحالية';

  @override
  String get profileNewPassword => 'كلمة المرور الجديدة';

  @override
  String get profileConfirmNewPassword => 'تأكيد كلمة المرور الجديدة';

  @override
  String get profileTwoFactorAuth => 'المصادقة الثنائية';

  @override
  String get profileTwoFactorAuthDescription =>
      'أضف طبقة إضافية من الأمان لحسابك.';

  @override
  String get profileTwoFactorEnable => 'تفعيل المصادقة الثنائية';

  @override
  String get profileTwoFactorDisable => 'تعطيل المصادقة الثنائية';

  @override
  String get profileTwoFactorSetup => 'إعداد المصادقة الثنائية';

  @override
  String get profileTwoFactorScanQr => 'امسح رمز QR هذا بتطبيق المصادقة.';

  @override
  String get profileTwoFactorEnterCode =>
      'أدخل الرمز المكون من 6 أرقام من تطبيق المصادقة.';

  @override
  String get profileTwoFactorBackupCodes => 'رموز الاسترداد';

  @override
  String get profileTwoFactorBackupCodesDescription =>
      'احفظ هذه الرموز في مكان آمن. يمكنك استخدامها لتسجيل الدخول إذا فقدت الوصول إلى تطبيق المصادقة.';

  @override
  String get profileOauthAccounts => 'الحسابات المرتبطة';

  @override
  String get profileOauthAccountsDescription =>
      'إدارة حساباتك الاجتماعية المرتبطة.';

  @override
  String get profileOauthLink => 'ربط حساب';

  @override
  String get profileOauthUnlink => 'إلغاء الربط';

  @override
  String get profileOauthUnlinkConfirm =>
      'هل أنت متأكد أنك تريد إلغاء ربط هذا الحساب؟';

  @override
  String get profileTrustedDevices => 'الأجهزة الموثوقة';

  @override
  String get profileTrustedDevicesDescription =>
      'إدارة الأجهزة التي يمكنها الوصول إلى حسابك.';

  @override
  String get profileDeviceCurrent => 'الجهاز الحالي';

  @override
  String profileDeviceLastActive(String date) {
    return 'آخر نشاط $date';
  }

  @override
  String get profileDeviceRevoke => 'إلغاء الوصول';

  @override
  String get profileDeviceRevokeConfirm =>
      'هل أنت متأكد أنك تريد إلغاء وصول هذا الجهاز؟';

  @override
  String get profileDeviceRevokeAll => 'إلغاء وصول جميع الأجهزة';

  @override
  String get profileDeleteAccount => 'حذف الحساب';

  @override
  String get profileDeleteAccountDescription =>
      'حذف حسابك وجميع البيانات المرتبطة به نهائيًا.';

  @override
  String get profileDeleteAccountConfirm =>
      'هل أنت متأكد أنك تريد حذف حسابك؟ لا يمكن التراجع عن هذا الإجراء.';

  @override
  String get profileDeleteAccountButton => 'حذف حسابي';

  @override
  String get profileSubscriptionStatus => 'حالة الاشتراك';

  @override
  String profileMemberSince(String date) {
    return 'عضو منذ $date';
  }

  @override
  String get configImportTitle => 'استيراد الإعدادات';

  @override
  String get configImportQrScanTitle => 'مسح رمز QR';

  @override
  String get configImportQrScanDescription =>
      'وجّه الكاميرا نحو رمز QR لإعدادات VPN.';

  @override
  String get configImportScanQrButton => 'مسح رمز QR';

  @override
  String get configImportFromClipboard => 'استيراد من الحافظة';

  @override
  String get configImportFromClipboardDescription =>
      'الصق رابط أو نص إعدادات من الحافظة.';

  @override
  String get configImportFromFile => 'استيراد من ملف';

  @override
  String get configImportFromFileDescription => 'حدد ملف إعدادات من جهازك.';

  @override
  String get configImportPreviewTitle => 'معاينة الإعدادات';

  @override
  String get configImportPreviewServer => 'الخادم';

  @override
  String get configImportPreviewProtocol => 'البروتوكول';

  @override
  String get configImportPreviewPort => 'المنفذ';

  @override
  String get configImportConfirmButton => 'استيراد الإعدادات';

  @override
  String get configImportCancelButton => 'إلغاء الاستيراد';

  @override
  String get configImportSuccess => 'تم استيراد الإعدادات بنجاح.';

  @override
  String get configImportError => 'فشل استيراد الإعدادات.';

  @override
  String get configImportInvalidFormat => 'تنسيق إعدادات غير صالح.';

  @override
  String get configImportDuplicate => 'هذه الإعدادات موجودة بالفعل.';

  @override
  String get configImportCameraPermission => 'مطلوب إذن الكاميرا لمسح رموز QR.';

  @override
  String get notificationCenterTitle => 'الإشعارات';

  @override
  String get notificationCenterEmpty => 'لا توجد إشعارات بعد.';

  @override
  String get notificationCenterMarkAllRead => 'تحديد الكل كمقروء';

  @override
  String get notificationCenterClearAll => 'مسح الكل';

  @override
  String get notificationTypeConnectionStatus => 'حالة الاتصال';

  @override
  String get notificationTypeServerSwitch => 'تبديل الخادم';

  @override
  String get notificationTypeSubscriptionExpiry => 'انتهاء الاشتراك';

  @override
  String get notificationTypeSecurityAlert => 'تنبيه أمني';

  @override
  String get notificationTypePromotion => 'عرض ترويجي';

  @override
  String get notificationTypeSystemUpdate => 'تحديث النظام';

  @override
  String notificationConnected(String serverName) {
    return 'متصل بـ $serverName';
  }

  @override
  String get notificationDisconnected => 'تم قطع الاتصال بـ VPN.';

  @override
  String notificationServerSwitched(String serverName) {
    return 'تم التبديل إلى $serverName.';
  }

  @override
  String notificationSubscriptionExpiring(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'ينتهي اشتراكك خلال $count يوم',
      many: 'ينتهي اشتراكك خلال $count يومًا',
      few: 'ينتهي اشتراكك خلال $count أيام',
      two: 'ينتهي اشتراكك خلال يومين',
      one: 'ينتهي اشتراكك خلال يوم واحد',
      zero: 'ينتهي اشتراكك اليوم',
    );
    return '$_temp0.';
  }

  @override
  String get notificationSubscriptionExpired =>
      'انتهى اشتراكك. جدد للاستمرار في استخدام CyberVPN.';

  @override
  String notificationUnreadCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count إشعار غير مقروء',
      many: '$count إشعارًا غير مقروء',
      few: '$count إشعارات غير مقروءة',
      two: 'إشعاران غير مقروءين',
      one: 'إشعار واحد غير مقروء',
      zero: 'لا توجد إشعارات غير مقروءة',
    );
    return '$_temp0';
  }

  @override
  String get referralDashboardTitle => 'برنامج الإحالة';

  @override
  String get referralDashboardDescription => 'ادعُ أصدقاءك واحصل على مكافآت.';

  @override
  String get referralShareLink => 'مشاركة رابط الإحالة';

  @override
  String get referralCopyLink => 'نسخ الرابط';

  @override
  String get referralLinkCopied => 'تم نسخ رابط الإحالة إلى الحافظة.';

  @override
  String get referralCodeLabel => 'رمز الإحالة الخاص بك';

  @override
  String referralRewardsEarned(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count مكافأة مكتسبة',
      many: '$count مكافأةً مكتسبةً',
      few: '$count مكافآت مكتسبة',
      two: 'مكافأتان مكتسبتان',
      one: 'مكافأة واحدة مكتسبة',
      zero: 'لا مكافآت مكتسبة',
    );
    return '$_temp0';
  }

  @override
  String referralFriendsInvited(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'تمت دعوة $count صديق',
      many: 'تمت دعوة $count صديقًا',
      few: 'تمت دعوة $count أصدقاء',
      two: 'تمت دعوة صديقين',
      one: 'تمت دعوة صديق واحد',
      zero: 'لم تتم دعوة أصدقاء',
    );
    return '$_temp0';
  }

  @override
  String referralRewardDescription(int days) {
    return 'احصل على $days أيام مجانية لكل صديق يشترك.';
  }

  @override
  String get referralHistory => 'سجل الإحالات';

  @override
  String get referralPending => 'قيد الانتظار';

  @override
  String get referralCompleted => 'مكتمل';

  @override
  String get referralExpired => 'منتهي الصلاحية';

  @override
  String get diagnosticsTitle => 'التشخيصات';

  @override
  String get diagnosticsDescription => 'اختبر اتصالك واستكشف المشكلات.';

  @override
  String get speedTestTitle => 'اختبار السرعة';

  @override
  String get speedTestStart => 'بدء اختبار السرعة';

  @override
  String get speedTestRunning => 'جارٍ الاختبار...';

  @override
  String get speedTestDownloadSpeed => 'سرعة التنزيل';

  @override
  String get speedTestUploadSpeed => 'سرعة الرفع';

  @override
  String get speedTestPing => 'زمن الاستجابة';

  @override
  String speedTestPingMs(int value) {
    return '$value مللي ثانية';
  }

  @override
  String speedTestMbps(String value) {
    return '$value ميغابت/ث';
  }

  @override
  String get speedTestResult => 'نتيجة اختبار السرعة';

  @override
  String get speedTestHistory => 'سجل اختبارات السرعة';

  @override
  String get speedTestStepConnecting => 'جارٍ الاتصال بخادم الاختبار...';

  @override
  String get speedTestStepDownload => 'جارٍ اختبار سرعة التنزيل...';

  @override
  String get speedTestStepUpload => 'جارٍ اختبار سرعة الرفع...';

  @override
  String get speedTestStepPing => 'جارٍ قياس زمن الاستجابة...';

  @override
  String get speedTestStepComplete => 'اكتمل الاختبار.';

  @override
  String get speedTestNoVpn => 'اتصل بـ VPN قبل إجراء اختبار السرعة.';

  @override
  String get logViewerTitle => 'عارض السجلات';

  @override
  String get logViewerEmpty => 'لا توجد سجلات متاحة.';

  @override
  String get logViewerExportButton => 'تصدير السجلات';

  @override
  String get logViewerClearButton => 'مسح السجلات';

  @override
  String get logViewerClearConfirm => 'هل أنت متأكد أنك تريد مسح جميع السجلات؟';

  @override
  String get logViewerFilterLabel => 'تصفية';

  @override
  String get logViewerFilterAll => 'الكل';

  @override
  String get logViewerFilterError => 'أخطاء';

  @override
  String get logViewerFilterWarning => 'تحذيرات';

  @override
  String get logViewerFilterInfo => 'معلومات';

  @override
  String get logViewerCopied => 'تم نسخ إدخال السجل إلى الحافظة.';

  @override
  String get logViewerExportSuccess => 'تم تصدير السجلات بنجاح.';

  @override
  String get logViewerExportError => 'فشل تصدير السجلات.';

  @override
  String get widgetConnectLabel => 'اتصل بـ VPN';

  @override
  String get widgetDisconnectLabel => 'اقطع VPN';

  @override
  String get widgetStatusLabel => 'حالة VPN';

  @override
  String get widgetServerLabel => 'الخادم الحالي';

  @override
  String get quickActionConnect => 'اتصال';

  @override
  String get quickActionDisconnect => 'قطع';

  @override
  String get quickActionServers => 'الخوادم';

  @override
  String get quickActionSpeedTest => 'اختبار السرعة';

  @override
  String get quickActionSettings => 'الإعدادات';

  @override
  String get quickActionSupport => 'الدعم';

  @override
  String get errorConnectionFailed => 'فشل الاتصال. يرجى المحاولة مرة أخرى.';

  @override
  String get errorConnectionTimeout =>
      'انتهت مهلة الاتصال. تحقق من اتصالك بالإنترنت.';

  @override
  String get errorServerUnavailable =>
      'الخادم غير متاح حاليًا. جرب خادمًا آخر.';

  @override
  String get errorInvalidConfig =>
      'إعدادات غير صالحة. يرجى إعادة استيراد إعداداتك.';

  @override
  String get errorSubscriptionExpired =>
      'انتهى اشتراكك. يرجى التجديد للاستمرار.';

  @override
  String get errorSubscriptionRequired => 'يلزم اشتراك لاستخدام هذه الميزة.';

  @override
  String get errorAuthenticationFailed =>
      'فشلت المصادقة. يرجى تسجيل الدخول مرة أخرى.';

  @override
  String get errorTokenExpired => 'انتهت الجلسة. يرجى تسجيل الدخول مرة أخرى.';

  @override
  String get errorNetworkUnreachable =>
      'الشبكة غير قابلة للوصول. تحقق من اتصالك.';

  @override
  String get errorPermissionDenied => 'تم رفض الإذن.';

  @override
  String get errorRateLimited => 'طلبات كثيرة جدًا. يرجى الانتظار لحظة.';

  @override
  String get errorUnexpected => 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.';

  @override
  String get errorServerError => 'خطأ في الخادم. يرجى المحاولة لاحقًا.';

  @override
  String get errorInvalidCredentials => 'بريد إلكتروني أو كلمة مرور غير صحيحة.';

  @override
  String get errorAccountLocked => 'تم قفل حسابك. يرجى التواصل مع الدعم.';

  @override
  String get errorWeakPassword =>
      'كلمة المرور ضعيفة جدًا. استخدم 8 أحرف على الأقل مع حروف وأرقام.';

  @override
  String get errorEmailAlreadyInUse => 'هذا البريد الإلكتروني مسجل بالفعل.';

  @override
  String get errorInvalidEmail => 'يرجى إدخال عنوان بريد إلكتروني صالح.';

  @override
  String get errorFieldRequired => 'هذا الحقل مطلوب.';

  @override
  String get errorPaymentFailed =>
      'فشل الدفع. يرجى المحاولة مرة أخرى أو استخدام طريقة أخرى.';

  @override
  String get errorQrScanFailed => 'فشل مسح رمز QR. يرجى المحاولة مرة أخرى.';

  @override
  String get a11yConnectButton => 'اتصل بخادم VPN';

  @override
  String get a11yDisconnectButton => 'اقطع الاتصال بخادم VPN';

  @override
  String get a11yServerStatusOnline => 'الخادم متصل';

  @override
  String get a11yServerStatusOffline => 'الخادم غير متصل';

  @override
  String get a11yServerStatusMaintenance => 'الخادم قيد الصيانة';

  @override
  String a11ySpeedIndicator(String speed) {
    return 'السرعة الحالية: $speed';
  }

  @override
  String a11yConnectionStatus(String status) {
    return 'حالة الاتصال: $status';
  }

  @override
  String a11yServerSelect(String name, String country) {
    return 'اختر خادم $name في $country';
  }

  @override
  String get a11yNavigationMenu => 'قائمة التنقل';

  @override
  String get a11yCloseDialog => 'إغلاق الحوار';

  @override
  String a11yToggleSwitch(String label) {
    return 'تبديل $label';
  }

  @override
  String a11yNotificationBadge(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count إشعار',
      many: '$count إشعارًا',
      few: '$count إشعارات',
      two: 'إشعاران',
      one: 'إشعار واحد',
      zero: 'لا توجد إشعارات',
    );
    return '$_temp0';
  }

  @override
  String get a11yLoadingIndicator => 'جارٍ التحميل';

  @override
  String get a11yRefreshContent => 'تحديث المحتوى';

  @override
  String get a11yBackButton => 'رجوع';

  @override
  String get a11ySearchField => 'بحث';

  @override
  String get rootDetectionDialogTitle => 'Rooted/Jailbroken Device Detected';

  @override
  String get rootDetectionDialogDescription =>
      'Your device appears to be rooted (Android) or jailbroken (iOS). While CyberVPN will continue to work, please note that using a rooted/jailbroken device may expose you to security risks.\n\nWe understand that users in censored regions often rely on rooted devices for additional privacy tools. CyberVPN will not block your access, but we recommend being cautious about the apps you install and the permissions you grant.';

  @override
  String get rootDetectionDialogDismiss => 'I Understand';
}
