// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Hebrew (`he`).
class AppLocalizationsHe extends AppLocalizations {
  AppLocalizationsHe([String locale = 'he']) : super(locale);

  @override
  String get appName => 'CyberVPN';

  @override
  String get login => 'כניסה';

  @override
  String get register => 'הרשמה';

  @override
  String get email => 'אימייל';

  @override
  String get password => 'סיסמה';

  @override
  String get confirmPassword => 'אימות סיסמה';

  @override
  String get forgotPassword => 'שכחת סיסמה?';

  @override
  String get orContinueWith => 'או המשך עם';

  @override
  String get connect => 'התחבר';

  @override
  String get disconnect => 'התנתק';

  @override
  String get connecting => 'מתחבר...';

  @override
  String get disconnecting => 'מתנתק...';

  @override
  String get connected => 'מחובר';

  @override
  String get disconnected => 'מנותק';

  @override
  String get servers => 'שרתים';

  @override
  String get subscription => 'מנוי';

  @override
  String get settings => 'הגדרות';

  @override
  String get profile => 'פרופיל';

  @override
  String get selectServer => 'בחר שרת';

  @override
  String get autoSelect => 'בחירה אוטומטית';

  @override
  String get fastestServer => 'השרת המהיר ביותר';

  @override
  String get nearestServer => 'השרת הקרוב ביותר';

  @override
  String get killSwitch => 'מתג חירום';

  @override
  String get splitTunneling => 'מנהרה מפוצלת';

  @override
  String get autoConnect => 'חיבור אוטומטי';

  @override
  String get language => 'שפה';

  @override
  String get theme => 'ערכת נושא';

  @override
  String get darkMode => 'מצב כהה';

  @override
  String get lightMode => 'מצב בהיר';

  @override
  String get systemDefault => 'ברירת מחדל מערכת';

  @override
  String get logout => 'התנתקות';

  @override
  String get logoutConfirm => 'האם אתה בטוח שברצונך להתנתק?';

  @override
  String get cancel => 'ביטול';

  @override
  String get confirm => 'אישור';

  @override
  String get retry => 'נסה שוב';

  @override
  String get errorOccurred => 'אירעה שגיאה';

  @override
  String get noInternet => 'אין חיבור לאינטרנט';

  @override
  String get downloadSpeed => 'הורדה';

  @override
  String get uploadSpeed => 'העלאה';

  @override
  String get connectionTime => 'זמן חיבור';

  @override
  String get dataUsed => 'נתונים שנצרכו';

  @override
  String get currentPlan => 'תוכנית נוכחית';

  @override
  String get upgradePlan => 'שדרג תוכנית';

  @override
  String daysRemaining(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'נותרו $count ימים',
      two: 'נותרו יומיים',
      one: 'נותר יום אחד',
    );
    return '$_temp0';
  }

  @override
  String get referral => 'הפניה';

  @override
  String get shareReferralCode => 'שתף קוד הפניה';

  @override
  String get support => 'תמיכה';

  @override
  String get privacyPolicy => 'מדיניות פרטיות';

  @override
  String get termsOfService => 'תנאי שימוש';

  @override
  String version(String version) {
    return 'גרסה $version';
  }

  @override
  String get onboardingWelcomeTitle => 'ברוך הבא ל-CyberVPN';

  @override
  String get onboardingWelcomeDescription =>
      'גישה מאובטחת, מהירה ופרטית לאינטרנט בקצות אצבעותיך.';

  @override
  String get onboardingFeaturesTitle => 'תכונות חזקות';

  @override
  String get onboardingFeaturesDescription =>
      'מתג חירום, מנהרה מפוצלת והצפנה ברמה צבאית לשמירה על בטיחותך.';

  @override
  String get onboardingPrivacyTitle => 'הפרטיות שלך חשובה';

  @override
  String get onboardingPrivacyDescription =>
      'מדיניות אפס תיעוד. אנחנו אף פעם לא עוקבים, מאחסנים או משתפים את נתוני הגלישה שלך.';

  @override
  String get onboardingSpeedTitle => 'מהיר כברק';

  @override
  String get onboardingSpeedDescription =>
      'התחבר לשרתים מוטבים ברחבי העולם למהירויות הטובות ביותר.';

  @override
  String get onboardingSkip => 'דלג';

  @override
  String get onboardingNext => 'הבא';

  @override
  String get onboardingGetStarted => 'התחל';

  @override
  String get onboardingBack => 'חזור';

  @override
  String onboardingPageIndicator(int current, int total) {
    return 'עמוד $current מתוך $total';
  }

  @override
  String get settingsTitle => 'הגדרות';

  @override
  String get settingsGeneral => 'כללי';

  @override
  String get settingsVpn => 'הגדרות VPN';

  @override
  String get settingsAppearance => 'מראה';

  @override
  String get settingsDebug => 'איתור באגים';

  @override
  String get settingsNotifications => 'התראות';

  @override
  String get settingsAbout => 'אודות';

  @override
  String get settingsVpnProtocolLabel => 'פרוטוקול';

  @override
  String get settingsVpnProtocolDescription =>
      'בחר את פרוטוקול ה-VPN לחיבורים.';

  @override
  String get settingsAutoConnectLabel => 'חיבור אוטומטי';

  @override
  String get settingsAutoConnectDescription =>
      'התחבר אוטומטית כשהאפליקציה נפתחת.';

  @override
  String get settingsKillSwitchLabel => 'מתג חירום';

  @override
  String get settingsKillSwitchDescription =>
      'חסום אינטרנט אם חיבור ה-VPN נופל.';

  @override
  String get settingsDnsLabel => 'DNS מותאם אישית';

  @override
  String get settingsDnsDescription => 'השתמש בשרת DNS מותאם אישית.';

  @override
  String get settingsDnsPlaceholder => 'הזן כתובת DNS';

  @override
  String get settingsSplitTunnelingLabel => 'מנהרה מפוצלת';

  @override
  String get settingsSplitTunnelingDescription =>
      'בחר אילו אפליקציות משתמשות בחיבור VPN.';

  @override
  String get settingsThemeModeLabel => 'מצב ערכת נושא';

  @override
  String get settingsThemeModeDescription =>
      'בחר בין ערכת נושא בהירה, כהה או מערכת.';

  @override
  String get settingsLanguageLabel => 'שפה';

  @override
  String get settingsLanguageDescription => 'בחר את השפה המועדפת.';

  @override
  String get settingsDebugLogsLabel => 'ספרות איתור באגים';

  @override
  String get settingsDebugLogsDescription => 'הפעל תיעוד מפורט לפתרון בעיות.';

  @override
  String get settingsExportLogsLabel => 'ייצוא ספרות';

  @override
  String get settingsExportLogsDescription => 'ייצוא ספרות איתור באגים לתמיכה.';

  @override
  String get settingsResetLabel => 'איפוס הגדרות';

  @override
  String get settingsResetDescription => 'שחזר את כל ההגדרות לערכי ברירת מחדל.';

  @override
  String get settingsResetConfirm =>
      'האם אתה בטוח שברצונך לאפס את כל ההגדרות לברירת מחדל?';

  @override
  String get settingsStartOnBootLabel => 'הפעלה באתחול';

  @override
  String get settingsStartOnBootDescription =>
      'הפעל את CyberVPN אוטומטית כשהמכשיר נדלק.';

  @override
  String get settingsConnectionTimeoutLabel => 'זמן קצוב חיבור';

  @override
  String get settingsConnectionTimeoutDescription =>
      'זמן מרבי להמתנה לפני ביטול ניסיון התחברות.';

  @override
  String settingsConnectionTimeoutSeconds(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count שניות',
      two: 'שתי שניות',
      one: 'שנייה אחת',
    );
    return '$_temp0';
  }

  @override
  String get profileDashboard => 'לוח בקרה של פרופיל';

  @override
  String get profileEditProfile => 'עריכת פרופיל';

  @override
  String get profileDisplayName => 'שם תצוגה';

  @override
  String get profileEmailAddress => 'כתובת אימייל';

  @override
  String get profileChangePassword => 'שינוי סיסמה';

  @override
  String get profileCurrentPassword => 'סיסמה נוכחית';

  @override
  String get profileNewPassword => 'סיסמה חדשה';

  @override
  String get profileConfirmNewPassword => 'אימות סיסמה חדשה';

  @override
  String get profileTwoFactorAuth => 'אימות דו-שלבי';

  @override
  String get profileTwoFactorAuthDescription =>
      'הוסף שכבת אבטחה נוספת לחשבונך.';

  @override
  String get profileTwoFactorEnable => 'הפעל אימות דו-שלבי';

  @override
  String get profileTwoFactorDisable => 'השבת אימות דו-שלבי';

  @override
  String get profileTwoFactorSetup => 'הגדרת אימות דו-שלבי';

  @override
  String get profileTwoFactorScanQr => 'סרוק את קוד ה-QR באפליקציית המאמת.';

  @override
  String get profileTwoFactorEnterCode =>
      'הזן את הקוד בן 6 ספרות מאפליקציית המאמת.';

  @override
  String get profileTwoFactorBackupCodes => 'קודי גיבוי';

  @override
  String get profileTwoFactorBackupCodesDescription =>
      'שמור את הקודים האלה במקום בטוח. תוכל להשתמש בהם לכניסה אם תאבד גישה לאפליקציית המאמת.';

  @override
  String get profileOauthAccounts => 'חשבונות מקושרים';

  @override
  String get profileOauthAccountsDescription =>
      'נהל את החשבונות החברתיים המקושרים.';

  @override
  String get profileOauthLink => 'קשר חשבון';

  @override
  String get profileOauthUnlink => 'בטל קישור';

  @override
  String get profileOauthUnlinkConfirm =>
      'האם אתה בטוח שברצונך לבטל קישור חשבון זה?';

  @override
  String get profileTrustedDevices => 'מכשירים מורשים';

  @override
  String get profileTrustedDevicesDescription =>
      'נהל את המכשירים שיכולים לגשת לחשבונך.';

  @override
  String get profileDeviceCurrent => 'מכשיר נוכחי';

  @override
  String profileDeviceLastActive(String date) {
    return 'פעיל לאחרונה $date';
  }

  @override
  String get profileDeviceRevoke => 'בטל גישה';

  @override
  String get profileDeviceRevokeConfirm =>
      'האם אתה בטוח שברצונך לבטל גישה למכשיר זה?';

  @override
  String get profileDeviceRevokeAll => 'בטל גישה לכל המכשירים';

  @override
  String get profileDeleteAccount => 'מחק חשבון';

  @override
  String get profileDeleteAccountDescription =>
      'מחק לצמיתות את החשבון וכל הנתונים המשויכים.';

  @override
  String get profileDeleteAccountConfirm =>
      'האם אתה בטוח שברצונך למחוק את החשבון? פעולה זו אינה ניתנת לביטול.';

  @override
  String get profileDeleteAccountButton => 'מחק את החשבון שלי';

  @override
  String get profileSubscriptionStatus => 'מצב מנוי';

  @override
  String profileMemberSince(String date) {
    return 'חבר מאז $date';
  }

  @override
  String get configImportTitle => 'ייבוא הגדרות';

  @override
  String get configImportQrScanTitle => 'סריקת קוד QR';

  @override
  String get configImportQrScanDescription =>
      'כוון את המצלמה לקוד QR של הגדרות VPN.';

  @override
  String get configImportScanQrButton => 'סרוק קוד QR';

  @override
  String get configImportFromClipboard => 'ייבוא מלוח גזירה';

  @override
  String get configImportFromClipboardDescription =>
      'הדבק קישור או טקסט הגדרות מלוח הגזירה.';

  @override
  String get configImportFromFile => 'ייבוא מקובץ';

  @override
  String get configImportFromFileDescription => 'בחר קובץ הגדרות מהמכשיר.';

  @override
  String get configImportPreviewTitle => 'תצוגה מקדימה של הגדרות';

  @override
  String get configImportPreviewServer => 'שרת';

  @override
  String get configImportPreviewProtocol => 'פרוטוקול';

  @override
  String get configImportPreviewPort => 'פורט';

  @override
  String get configImportConfirmButton => 'ייבא הגדרות';

  @override
  String get configImportCancelButton => 'בטל ייבוא';

  @override
  String get configImportSuccess => 'ההגדרות יובאו בהצלחה.';

  @override
  String get configImportError => 'ייבוא ההגדרות נכשל.';

  @override
  String get configImportInvalidFormat => 'פורמט הגדרות לא תקין.';

  @override
  String get configImportDuplicate => 'הגדרות אלה כבר קיימות.';

  @override
  String get configImportCameraPermission =>
      'נדרשת הרשאת מצלמה לסריקת קודי QR.';

  @override
  String get notificationCenterTitle => 'התראות';

  @override
  String get notificationCenterEmpty => 'אין התראות עדיין.';

  @override
  String get notificationCenterMarkAllRead => 'סמן הכל כנקרא';

  @override
  String get notificationCenterClearAll => 'נקה הכל';

  @override
  String get notificationTypeConnectionStatus => 'מצב חיבור';

  @override
  String get notificationTypeServerSwitch => 'החלפת שרת';

  @override
  String get notificationTypeSubscriptionExpiry => 'פקיעת מנוי';

  @override
  String get notificationTypeSecurityAlert => 'התראת אבטחה';

  @override
  String get notificationTypePromotion => 'מבצע';

  @override
  String get notificationTypeSystemUpdate => 'עדכון מערכת';

  @override
  String notificationConnected(String serverName) {
    return 'מחובר ל-$serverName';
  }

  @override
  String get notificationDisconnected => 'התנתק מ-VPN.';

  @override
  String notificationServerSwitched(String serverName) {
    return 'הוחלף ל-$serverName.';
  }

  @override
  String notificationSubscriptionExpiring(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'המנוי שלך פג תוקף בעוד $count ימים',
      two: 'המנוי שלך פג תוקף בעוד יומיים',
      one: 'המנוי שלך פג תוקף בעוד יום אחד',
    );
    return '$_temp0.';
  }

  @override
  String get notificationSubscriptionExpired =>
      'המנוי שלך פג תוקף. חדש כדי להמשיך להשתמש ב-CyberVPN.';

  @override
  String notificationUnreadCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count התראות שלא נקראו',
      two: 'שתי התראות שלא נקראו',
      one: 'התראה אחת שלא נקראה',
    );
    return '$_temp0';
  }

  @override
  String get referralDashboardTitle => 'תוכנית הפניות';

  @override
  String get referralDashboardDescription => 'הזמן חברים וקבל פרסים.';

  @override
  String get referralShareLink => 'שתף קישור הפניה';

  @override
  String get referralCopyLink => 'העתק קישור';

  @override
  String get referralLinkCopied => 'קישור ההפניה הועתק ללוח הגזירה.';

  @override
  String get referralCodeLabel => 'קוד ההפניה שלך';

  @override
  String referralRewardsEarned(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count פרסים שהתקבלו',
      two: 'שני פרסים שהתקבלו',
      one: 'פרס אחד שהתקבל',
    );
    return '$_temp0';
  }

  @override
  String referralFriendsInvited(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count חברים הוזמנו',
      two: 'שני חברים הוזמנו',
      one: 'חבר אחד הוזמן',
    );
    return '$_temp0';
  }

  @override
  String referralRewardDescription(int days) {
    return 'קבל $days ימים חינם לכל חבר שנרשם.';
  }

  @override
  String get referralHistory => 'היסטוריית הפניות';

  @override
  String get referralPending => 'ממתין';

  @override
  String get referralCompleted => 'הושלם';

  @override
  String get referralExpired => 'פג תוקף';

  @override
  String get diagnosticsTitle => 'אבחונים';

  @override
  String get diagnosticsDescription => 'בדוק את החיבור ופתור בעיות.';

  @override
  String get speedTestTitle => 'בדיקת מהירות';

  @override
  String get speedTestStart => 'התחל בדיקת מהירות';

  @override
  String get speedTestRunning => 'בודק...';

  @override
  String get speedTestDownloadSpeed => 'מהירות הורדה';

  @override
  String get speedTestUploadSpeed => 'מהירות העלאה';

  @override
  String get speedTestPing => 'זמן תגובה';

  @override
  String speedTestPingMs(int value) {
    return '$value מילישניות';
  }

  @override
  String speedTestMbps(String value) {
    return '$value מגה\"ש';
  }

  @override
  String get speedTestResult => 'תוצאת בדיקת מהירות';

  @override
  String get speedTestHistory => 'היסטוריית בדיקות מהירות';

  @override
  String get speedTestStepConnecting => 'מתחבר לשרת הבדיקה...';

  @override
  String get speedTestStepDownload => 'בודק מהירות הורדה...';

  @override
  String get speedTestStepUpload => 'בודק מהירות העלאה...';

  @override
  String get speedTestStepPing => 'מודד זמן תגובה...';

  @override
  String get speedTestStepComplete => 'הבדיקה הושלמה.';

  @override
  String get speedTestNoVpn => 'התחבר ל-VPN לפני הפעלת בדיקת מהירות.';

  @override
  String get logViewerTitle => 'מציג ספרות';

  @override
  String get logViewerEmpty => 'אין ספרות זמינות.';

  @override
  String get logViewerExportButton => 'ייצוא ספרות';

  @override
  String get logViewerClearButton => 'נקה ספרות';

  @override
  String get logViewerClearConfirm =>
      'האם אתה בטוח שברצונך לנקות את כל הספרות?';

  @override
  String get logViewerFilterLabel => 'סינון';

  @override
  String get logViewerFilterAll => 'הכל';

  @override
  String get logViewerFilterError => 'שגיאות';

  @override
  String get logViewerFilterWarning => 'אזהרות';

  @override
  String get logViewerFilterInfo => 'מידע';

  @override
  String get logViewerCopied => 'רשומת הספר הועתקה ללוח הגזירה.';

  @override
  String get logViewerExportSuccess => 'הספרות יוצאו בהצלחה.';

  @override
  String get logViewerExportError => 'ייצוא הספרות נכשל.';

  @override
  String get widgetConnectLabel => 'התחבר ל-VPN';

  @override
  String get widgetDisconnectLabel => 'התנתק מ-VPN';

  @override
  String get widgetStatusLabel => 'מצב VPN';

  @override
  String get widgetServerLabel => 'שרת נוכחי';

  @override
  String get quickActionConnect => 'התחבר';

  @override
  String get quickActionDisconnect => 'התנתק';

  @override
  String get quickActionServers => 'שרתים';

  @override
  String get quickActionSpeedTest => 'בדיקת מהירות';

  @override
  String get quickActionSettings => 'הגדרות';

  @override
  String get quickActionSupport => 'תמיכה';

  @override
  String get errorConnectionFailed => 'החיבור נכשל. נסה שוב.';

  @override
  String get errorConnectionTimeout =>
      'זמן החיבור הסתיים. בדוק את חיבור האינטרנט.';

  @override
  String get errorServerUnavailable => 'השרת אינו זמין כרגע. נסה שרת אחר.';

  @override
  String get errorInvalidConfig => 'הגדרות לא תקינות. ייבא מחדש את ההגדרות.';

  @override
  String get errorSubscriptionExpired => 'המנוי שלך פג תוקף. חדש כדי להמשיך.';

  @override
  String get errorSubscriptionRequired => 'נדרש מנוי לשימוש בתכונה זו.';

  @override
  String get errorAuthenticationFailed => 'האימות נכשל. התחבר שוב.';

  @override
  String get errorTokenExpired => 'הפגישה פגה תוקף. התחבר שוב.';

  @override
  String get errorNetworkUnreachable => 'הרשת אינה נגישה. בדוק את החיבור.';

  @override
  String get errorPermissionDenied => 'הגישה נדחתה.';

  @override
  String get errorRateLimited => 'יותר מדי בקשות. המתן רגע.';

  @override
  String get errorUnexpected => 'אירעה שגיאה בלתי צפויה. נסה שוב.';

  @override
  String get errorServerError => 'שגיאת שרת. נסה שוב מאוחר יותר.';

  @override
  String get errorInvalidCredentials => 'אימייל או סיסמה שגויים.';

  @override
  String get errorAccountLocked => 'החשבון שלך ננעל. פנה לתמיכה.';

  @override
  String get errorWeakPassword =>
      'הסיסמה חלשה מדי. השתמש בלפחות 8 תווים עם אותיות ומספרים.';

  @override
  String get errorEmailAlreadyInUse => 'אימייל זה כבר רשום.';

  @override
  String get errorInvalidEmail => 'הזן כתובת אימייל תקינה.';

  @override
  String get errorFieldRequired => 'שדה זה נדרש.';

  @override
  String get errorPaymentFailed =>
      'התשלום נכשל. נסה שוב או השתמש באמצעי תשלום אחר.';

  @override
  String get errorQrScanFailed => 'סריקת קוד QR נכשלה. נסה שוב.';

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
  String get a11yConnectButton => 'התחבר לשרת VPN';

  @override
  String get a11yDisconnectButton => 'התנתק משרת VPN';

  @override
  String get a11yServerStatusOnline => 'השרת מחובר';

  @override
  String get a11yServerStatusOffline => 'השרת מנותק';

  @override
  String get a11yServerStatusMaintenance => 'השרת בתחזוקה';

  @override
  String a11ySpeedIndicator(String speed) {
    return 'מהירות נוכחית: $speed';
  }

  @override
  String a11yConnectionStatus(String status) {
    return 'מצב חיבור: $status';
  }

  @override
  String a11yServerSelect(String name, String country) {
    return 'בחר שרת $name ב-$country';
  }

  @override
  String get a11yNavigationMenu => 'תפריט ניווט';

  @override
  String get a11yCloseDialog => 'סגור חלון';

  @override
  String a11yToggleSwitch(String label) {
    return 'החלף $label';
  }

  @override
  String a11yNotificationBadge(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count התראות',
      two: 'שתי התראות',
      one: 'התראה אחת',
    );
    return '$_temp0';
  }

  @override
  String get a11yLoadingIndicator => 'טוען';

  @override
  String get a11yRefreshContent => 'רענן תוכן';

  @override
  String get a11yBackButton => 'חזור';

  @override
  String get a11ySearchField => 'חיפוש';

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
