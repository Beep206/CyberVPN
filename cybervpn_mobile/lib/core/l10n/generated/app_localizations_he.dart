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
}
