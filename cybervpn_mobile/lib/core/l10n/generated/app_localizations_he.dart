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
  String get onboardingConnectTitle => 'One Tap Connect';

  @override
  String get onboardingConnectDescription =>
      'Connect to hundreds of servers worldwide with a single tap.';

  @override
  String get onboardingGlobeTitle => 'Global Network';

  @override
  String get onboardingGlobeDescription =>
      'Access content from anywhere with our worldwide server network.';

  @override
  String get onboardingGetStartedTitle => 'Ready to Go';

  @override
  String get onboardingGetStartedDescription =>
      'Your secure connection is just one tap away.';

  @override
  String get onboardingNoPages => 'No onboarding pages';

  @override
  String get permissionSetupTitle => 'Set Up Permissions';

  @override
  String get permissionSetupSubtitle =>
      'CyberVPN needs a few permissions to keep you secure';

  @override
  String get permissionVpnTitle => 'VPN Connection';

  @override
  String get permissionVpnDescription =>
      'CyberVPN creates a secure tunnel to protect your data';

  @override
  String get permissionGrantButton => 'Grant Permissions';

  @override
  String get permissionContinueAnyway => 'Continue Anyway';

  @override
  String get permissionAllSet => 'All Set!';

  @override
  String get permissionAlmostReady => 'Almost Ready';

  @override
  String get permissionEnableLater =>
      'You can enable these permissions later in Settings if needed';

  @override
  String get permissionAppReady => 'Your app is configured and ready to use';

  @override
  String get permissionOpenSettings => 'Open Settings';

  @override
  String get permissionEnableInSettings =>
      'Please enable permissions in your device Settings';

  @override
  String get settingsTitle => 'הגדרות';

  @override
  String get settingsSearchHint => 'Search settings...';

  @override
  String get settingsSelectCategory => 'Select a category';

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
  String get configImportPasteLink => '[EN] Paste VPN config link';

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
  String get notificationCenterEmptyDescription =>
      'When you receive notifications, they will appear here.';

  @override
  String get notificationCenterLoadError => 'Failed to load notifications';

  @override
  String get notificationCenterDismissed => 'Notification dismissed';

  @override
  String get notificationTimeJustNow => 'Just now';

  @override
  String notificationTimeMinutesAgo(int count) {
    return '${count}m ago';
  }

  @override
  String notificationTimeHoursAgo(int count) {
    return '${count}h ago';
  }

  @override
  String notificationTimeDaysAgo(int count) {
    return '${count}d ago';
  }

  @override
  String notificationTimeWeeksAgo(int count) {
    return '${count}w ago';
  }

  @override
  String notificationTimeMonthsAgo(int count) {
    return '${count}mo ago';
  }

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
  String get loginSigningIn => '[EN] Signing in, please wait';

  @override
  String get loginHint => '[EN] Sign in to your account';

  @override
  String get loginContinueWithTelegram => 'Continue with Telegram';

  @override
  String get loginTitle => '[EN] CyberVPN';

  @override
  String get loginSubtitle => '[EN] Secure your connection';

  @override
  String get loginOrUsePassword => '[EN] OR USE PASSWORD';

  @override
  String get loginOrSeparator => '[EN] OR';

  @override
  String get loginNoAccount => '[EN] Don\'t have an account? ';

  @override
  String get loginRegisterLink => '[EN] Register';

  @override
  String get loginBiometricFaceId => '[EN] Sign in with Face ID';

  @override
  String get loginBiometricFingerprint => '[EN] Sign in with fingerprint';

  @override
  String get loginBiometricGeneric => '[EN] Sign in with biometrics';

  @override
  String get loginBiometricAuthenticating =>
      '[EN] Authenticating with biometrics, please wait';

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
  String get appLockBiometricFaceId => '[EN] Face ID';

  @override
  String get appLockBiometricFingerprint => '[EN] fingerprint';

  @override
  String get appLockBiometricGeneric => '[EN] biometrics';

  @override
  String get appLockAuthenticating => '[EN] Authenticating, please wait';

  @override
  String get appLockUnlockHint => '[EN] Authenticate to unlock the app';

  @override
  String get appLockPinHint => '[EN] Unlock using your device PIN or passcode';

  @override
  String appLockFailedAttempts(int current, int max) {
    return '[EN] Failed attempts: $current/$max';
  }

  @override
  String appLockFailedAttemptsA11y(int current, int max) {
    return '[EN] Failed authentication attempts: $current out of $max';
  }

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
  String get biometricSignInReason => '[EN] Sign in to CyberVPN';

  @override
  String get biometricSignInHint => '[EN] Use biometrics to sign in quickly';

  @override
  String get formEmailLabel => '[EN] Email';

  @override
  String get formEmailHint => '[EN] Enter your email';

  @override
  String get formPasswordLabel => '[EN] Password';

  @override
  String get formPasswordHint => '[EN] Enter your password';

  @override
  String get formShowPassword => '[EN] Show password';

  @override
  String get formHidePassword => '[EN] Hide password';

  @override
  String get registerPasswordStrengthWeak => '[EN] Weak';

  @override
  String get registerPasswordStrengthMedium => '[EN] Medium';

  @override
  String get registerPasswordStrengthStrong => '[EN] Strong';

  @override
  String get registerAcceptTermsA11y =>
      '[EN] Accept Terms and Conditions and Privacy Policy';

  @override
  String get registerAcceptTermsA11yHint => '[EN] Required to create account';

  @override
  String get registerReferralValidA11y => '[EN] Valid referral code';

  @override
  String get registerReferralAppliedA11y =>
      '[EN] Referral code applied successfully';

  @override
  String get registerCreatingAccount => '[EN] Creating account, please wait';

  @override
  String get registerHint => '[EN] Create your account';

  @override
  String get registerLoginA11y => '[EN] Go to login screen';

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
  String subscriptionDaysRemaining(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'נשארו $count ימים',
      one: 'נשאר יום אחד',
    );
    return '$_temp0';
  }

  @override
  String get subscriptionExpiringSoon => 'פג תוקף בקרוב';

  @override
  String get subscriptionRenewNow => 'חדש עכשיו';

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
  String serverListCount(int shown, int total) {
    return '$shown of $total servers';
  }

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
  String get quickSetupReadyToProtect => 'Ready to protect you';

  @override
  String get quickSetupBestServer => 'We\'ve selected the best server for you';

  @override
  String get quickSetupFindingServer => 'Finding the best server...';

  @override
  String get quickSetupYoureProtected => 'You\'re protected!';

  @override
  String get quickSetupConnectionSecure => 'Your connection is now secure';

  @override
  String get quickSetupTakeYourTime =>
      'Take your time - you can connect anytime from the main screen';

  @override
  String get quickSetupNoServers =>
      'No available servers found. Please try again later.';

  @override
  String get quickSetupConnectionTimeout =>
      'Connection timeout. Please try selecting a different server.';

  @override
  String quickSetupConnectionFailed(String error) {
    return 'Connection failed: $error';
  }

  @override
  String get quickSetupChooseServer => 'Choose Server';

  @override
  String get splashLoading => 'Loading...';

  @override
  String get splashInitializing => 'Initializing...';

  @override
  String get profileDeviceManagement => 'Device Management';

  @override
  String profileDevicesConnected(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count devices connected',
      one: '1 device connected',
    );
    return '$_temp0';
  }

  @override
  String get profileDeviceLimitReached =>
      'Device limit reached. Remove a device to add new ones.';

  @override
  String get profileRemoveDevice => 'Remove Device';

  @override
  String profileRemoveDeviceConfirm(String deviceName) {
    return 'Remove $deviceName?\n\nYou\'ll need to log in again on this device if you want to use it later.';
  }

  @override
  String profileRemoveDeviceConfirmShort(String deviceName) {
    return 'Remove $deviceName?\n\nYou\'ll need to log in again on this device.';
  }

  @override
  String get profileRemovingDevice => 'Removing device...';

  @override
  String profileDeviceRemovedSuccess(String deviceName) {
    return '$deviceName removed successfully';
  }

  @override
  String profileRemoveDeviceFailed(String error) {
    return 'Failed to remove device: $error';
  }

  @override
  String get profileThisDevice => 'This device';

  @override
  String get profileRemoveDeviceTooltip => 'Remove device';

  @override
  String get profileNoDevicesConnected => 'No devices connected';

  @override
  String get profileConnectToRegister =>
      'Connect to VPN to register this device';

  @override
  String get profileDeviceLastActiveNever => 'Never';

  @override
  String get profileDeviceLastActiveJustNow => 'Just now';

  @override
  String profileDeviceLastActiveMinutes(int count) {
    return '${count}m ago';
  }

  @override
  String profileDeviceLastActiveHours(int count) {
    return '${count}h ago';
  }

  @override
  String profileDeviceLastActiveDays(int count) {
    return '${count}d ago';
  }

  @override
  String get profileRemoveButton => 'Remove';

  @override
  String get profileTwoFactorEnabled => '2FA Enabled';

  @override
  String get profileTwoFactorDisabledStatus => '2FA Disabled';

  @override
  String get profileTwoFactorProtected =>
      'Your account is protected with two-factor authentication';

  @override
  String get profileTwoFactorEnablePrompt =>
      'Enable 2FA to secure your account';

  @override
  String get profileTwoFactorWhatIs => 'What is Two-Factor Authentication?';

  @override
  String get profileTwoFactorFullDescription =>
      'Two-factor authentication (2FA) adds an extra layer of security to your account. You\'ll need both your password and a code from your authenticator app to sign in.';

  @override
  String get profileTwoFactorEnhancedSecurity => 'Enhanced Security';

  @override
  String get profileTwoFactorEnhancedSecurityDesc =>
      'Protects your account from unauthorized access';

  @override
  String get profileTwoFactorAuthenticatorApp => 'Authenticator App';

  @override
  String get profileTwoFactorAuthenticatorAppDesc =>
      'Use any TOTP app like Google Authenticator or Authy';

  @override
  String get profileTwoFactorBackupCodesDesc =>
      'Receive backup codes for account recovery';

  @override
  String get profileTwoFactorStep1 => 'Step 1: Scan QR Code';

  @override
  String get profileTwoFactorStep2 => 'Step 2: Verify Code';

  @override
  String get profileTwoFactorScanQrShort =>
      'Scan this QR code with your authenticator app';

  @override
  String get profileTwoFactorEnterManually => 'Enter manually';

  @override
  String get profileTwoFactorSecretKey => 'Secret Key:';

  @override
  String get profileTwoFactorEnterCodeShort =>
      'Enter the 6-digit code from your authenticator app';

  @override
  String get profileTwoFactorCodeLabel => '6-digit code';

  @override
  String get profileTwoFactorVerifyAndEnable => 'Verify and Enable';

  @override
  String get profileTwoFactorActive => 'Two-Factor Authentication is Active';

  @override
  String get profileTwoFactorActiveDesc =>
      'Your account is protected with two-factor authentication. You\'ll need to enter a code from your authenticator app every time you sign in.';

  @override
  String get profileTwoFactorViewBackupCodes => 'View Backup Codes';

  @override
  String get profileTwoFactorCopyAll => 'Copy All';

  @override
  String get profileTwoFactorBackupCodesInstructions =>
      'Save these backup codes in a safe place. Each code can only be used once to sign in if you lose access to your authenticator app.';

  @override
  String get profileTwoFactorDisableConfirmTitle =>
      'Disable Two-Factor Authentication?';

  @override
  String get profileTwoFactorDisableWarning =>
      'Disabling 2FA will make your account less secure. You\'ll only need your password to sign in.';

  @override
  String get profileTwoFactorDisableButton => 'Disable';

  @override
  String get profileTwoFactorEnterVerificationCode => 'Enter Verification Code';

  @override
  String get profileTwoFactorFailedSetupData => 'Failed to load setup data';

  @override
  String get profileSocialAccounts => 'Social Accounts';

  @override
  String get profileSocialAccountsDescription =>
      'Link your social accounts for easier sign-in and account recovery.';

  @override
  String get profileSocialLinked => 'Linked';

  @override
  String get profileSocialNotLinked => 'Not Linked';

  @override
  String get profileSocialLink => 'Link';

  @override
  String get profileSocialCompleteAuth =>
      'Complete authorization in your browser, then return to the app.';

  @override
  String profileSocialUnlinkConfirm(String provider) {
    return 'Unlink $provider?';
  }

  @override
  String profileSocialUnlinkDescription(String provider) {
    return 'You will need to re-authorize to link this account again. This will not delete your $provider account.';
  }

  @override
  String get profileGreetingMorning => 'Good morning';

  @override
  String get profileGreetingAfternoon => 'Good afternoon';

  @override
  String get profileGreetingEvening => 'Good evening';

  @override
  String get profileNoProfileData => 'No profile data available.';

  @override
  String get profileQuickActions => 'Quick Actions';

  @override
  String get profileInviteFriends => 'Invite Friends';

  @override
  String get profileSecuritySettings => 'Security Settings';

  @override
  String get profileStatsTraffic => 'Traffic';

  @override
  String get profileStatsUnlimited => 'Unlimited';

  @override
  String get profileStatsDaysLeft => 'Days Left';

  @override
  String get profileStatsDevices => 'Devices';

  @override
  String get profileStatsNoPlan => 'No Plan';

  @override
  String get profileSubActive => 'Active';

  @override
  String get profileSubTrial => 'Trial';

  @override
  String get profileSubExpired => 'Expired';

  @override
  String get profileSubCancelled => 'Cancelled';

  @override
  String get profileSubPending => 'Pending';

  @override
  String get profileDeleteDangerZoneDesc => 'This action cannot be undone';

  @override
  String get profileDeleteWhatWillBeDeleted => 'What will be deleted?';

  @override
  String get profileDeletePermanentlyDeleted =>
      'The following data will be permanently deleted:';

  @override
  String get profileDeletePersonalInfo => 'Personal Information';

  @override
  String get profileDeletePersonalInfoDesc =>
      'Email, username, and profile data';

  @override
  String get profileDeleteSubscriptionHistory =>
      'Subscription & Payment History';

  @override
  String get profileDeleteSubscriptionHistoryDesc =>
      'All active subscriptions and transaction records';

  @override
  String get profileDeleteVpnConfigs => 'VPN Configurations';

  @override
  String get profileDeleteVpnConfigsDesc =>
      'Server settings and connection preferences';

  @override
  String get profileDeleteAppSettings => 'App Settings';

  @override
  String get profileDeleteAppSettingsDesc =>
      'All preferences and customizations';

  @override
  String get profileDeleteGracePeriod => '30-Day Grace Period';

  @override
  String get profileDeleteGracePeriodDesc =>
      'Your account will be scheduled for deletion. You can cancel this request within 30 days by logging back in. After this period, all data will be permanently deleted.';

  @override
  String get profileDeleteStorePolicy =>
      'In compliance with App Store and Google Play data deletion policies, all personal data will be permanently removed from our servers.';

  @override
  String get profileDeleteContinue => 'Continue with Deletion';

  @override
  String get profileDeleteVerifyIdentity => 'Verify Your Identity';

  @override
  String get profileDeleteVerifyIdentityDesc =>
      'For security reasons, please re-enter your credentials to confirm account deletion.';

  @override
  String get profileDeletePasswordLabel => 'Password';

  @override
  String get profileDeletePasswordHint => 'Enter your password';

  @override
  String get profileDeleteVerifyAndContinue => 'Verify and Continue';

  @override
  String get profileDeleteFinalConfirmation => 'Final Confirmation';

  @override
  String get profileDeleteFinalConfirmationDesc =>
      'This is your last chance to cancel. Once confirmed, your account will be scheduled for permanent deletion.';

  @override
  String get profileDeleteIrreversible => 'This action is irreversible';

  @override
  String get profileDeleteIrreversibleList =>
      '• All data will be permanently deleted after 30 days\n• Active subscriptions will be cancelled\n• You will be immediately logged out\n• This cannot be undone';

  @override
  String get profileDeleteScheduledSuccess =>
      'Account deletion scheduled successfully';

  @override
  String get settingsVpnProtocolPreference => 'Protocol Preference';

  @override
  String get settingsAutoConnectOnLaunchLabel => 'Auto-connect on launch';

  @override
  String get settingsAutoConnectOnLaunchDescription =>
      'Connect to VPN when the app starts';

  @override
  String get settingsAutoConnectUntrustedWifiLabel =>
      'Auto-connect on untrusted WiFi';

  @override
  String get settingsAutoConnectUntrustedWifiDescription =>
      'Automatically connect when joining open networks';

  @override
  String get settingsManageTrustedNetworks => 'Manage trusted networks';

  @override
  String get settingsNoTrustedNetworks => 'No networks marked as trusted';

  @override
  String settingsTrustedNetworkCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count trusted networks',
      one: '1 trusted network',
    );
    return '$_temp0';
  }

  @override
  String get settingsSecuritySection => 'Security';

  @override
  String get settingsKillSwitchSubtitle =>
      'Block traffic if VPN disconnects unexpectedly';

  @override
  String get settingsKillSwitchDialogTitle => 'Enable Kill Switch?';

  @override
  String get settingsKillSwitchDialogContent =>
      'When enabled, all internet traffic will be blocked if the VPN connection drops unexpectedly. This protects your privacy but may temporarily prevent internet access.';

  @override
  String get settingsKillSwitchDialogEnable => 'Enable';

  @override
  String get settingsDnsProviderSection => 'DNS Provider';

  @override
  String get settingsDnsCustomAddressLabel => 'Custom DNS address';

  @override
  String get settingsDnsCustomAddressHint => 'e.g. 1.0.0.1';

  @override
  String get settingsAdvancedSection => 'Advanced';

  @override
  String get settingsSplitTunnelingSubtitle => 'Choose which apps use the VPN';

  @override
  String get settingsMtuAutoLabel => 'MTU: Auto';

  @override
  String get settingsMtuAutoDescription =>
      'Automatically determine optimal packet size';

  @override
  String get settingsMtuManualLabel => 'MTU: Manual';

  @override
  String get settingsMtuManualDescription => 'Set a custom MTU value';

  @override
  String get settingsMtuValueLabel => 'MTU value';

  @override
  String get settingsMtuValueHint => '1280-1500';

  @override
  String get settingsChangesApplyOnNextConnection =>
      'Changes apply on next connection';

  @override
  String get settingsLoadError => 'Failed to load settings';

  @override
  String settingsNotificationCountEnabled(int count) {
    return '$count of 4 enabled';
  }

  @override
  String get settingsAccountSecurity => 'Account & Security';

  @override
  String get settingsAccountSecuritySubtitle => 'Profile, password, 2FA';

  @override
  String get settingsVersionLabel => 'Version';

  @override
  String get settingsOpenSourceLicenses => 'Open-source licenses';

  @override
  String get settingsDebugDiagnostics => 'Debug & Diagnostics';

  @override
  String get settingsDebugAbout => 'Debug & About';

  @override
  String get settingsDebugAboutSubtitle =>
      'App version, logs, developer options';

  @override
  String get settingsCouldNotOpenUrl => 'Could not open URL';

  @override
  String get settingsDiagnosticsSection => 'Diagnostics';

  @override
  String settingsLogEntryCount(int count) {
    return '$count entries';
  }

  @override
  String get settingsCacheDataSection => 'Cache & Data';

  @override
  String get settingsClearCacheLabel => 'Clear Cache';

  @override
  String get settingsClearCacheDescription =>
      'Remove cached server lists and configs';

  @override
  String get settingsResetSubtitle => 'Restore defaults';

  @override
  String get settingsAppVersionLabel => 'App Version';

  @override
  String get settingsXrayCoreVersionLabel => 'Xray-core Version';

  @override
  String get settingsDeveloperOptions => 'Developer Options';

  @override
  String get settingsDeveloperRawConfig => 'Raw VPN Config Viewer';

  @override
  String get settingsDeveloperRawConfigSubtitle =>
      'View current Xray configuration';

  @override
  String get settingsDeveloperForceCrash => 'Force Crash (Sentry Test)';

  @override
  String get settingsDeveloperForceCrashSubtitle => 'Test error reporting';

  @override
  String get settingsDeveloperExperimental => 'Experimental Features';

  @override
  String get settingsDeveloperExperimentalSubtitle =>
      'Enable unreleased features';

  @override
  String get settingsLogLevelLabel => 'Log Level';

  @override
  String get settingsLogLevelDebug => 'Debug';

  @override
  String get settingsLogLevelInfo => 'Info';

  @override
  String get settingsLogLevelWarning => 'Warning';

  @override
  String get settingsLogLevelError => 'Error';

  @override
  String get settingsLogLevelDebugDescription =>
      'Detailed diagnostic information';

  @override
  String get settingsLogLevelInfoDescription =>
      'General informational messages';

  @override
  String get settingsLogLevelWarningDescription => 'Potential issues';

  @override
  String get settingsLogLevelErrorDescription => 'Errors only';

  @override
  String get settingsNoLogsToExport => 'No logs to export';

  @override
  String get settingsClearCacheDialogTitle => 'Clear Cache?';

  @override
  String get settingsClearCacheDialogContent =>
      'This will remove cached server lists and VPN configurations. Your settings will not be affected.';

  @override
  String get settingsClearCacheDialogConfirm => 'Clear';

  @override
  String get settingsCacheClearedSuccess => 'Cache cleared successfully';

  @override
  String get settingsResetDialogTitle => 'Reset All Settings?';

  @override
  String get settingsResetDialogContent =>
      'This will restore all settings to their default values. This action cannot be undone.';

  @override
  String get settingsResetDialogConfirm => 'Reset';

  @override
  String get settingsResetSuccess => 'Settings reset successfully';

  @override
  String get settingsDeveloperModeActivated => 'Developer mode activated';

  @override
  String get settingsDeveloperRawConfigDialogTitle => 'Raw VPN Config';

  @override
  String get settingsDeveloperForceCrashDialogTitle => 'Force Crash';

  @override
  String get settingsDeveloperForceCrashDialogContent =>
      'This will intentionally crash the app to test error reporting via Sentry. Only use this for debugging purposes.\n\nAre you sure you want to continue?';

  @override
  String get settingsDeveloperCrashNow => 'Crash Now';

  @override
  String get settingsNoLanguagesFound => 'No languages found';

  @override
  String get settingsTrustedNetworksTitle => 'Trusted Networks';

  @override
  String get settingsTrustedAddManually => 'Add network manually';

  @override
  String get settingsTrustedAddCurrentWifi => 'Add Current WiFi Network';

  @override
  String get settingsTrustedDetectingNetwork => 'Detecting network...';

  @override
  String get settingsTrustedInfoDescription =>
      'Trusted networks won\'t trigger auto-connect. Add your home or work WiFi networks here.';

  @override
  String get settingsTrustedEmptyTitle => 'No trusted networks';

  @override
  String get settingsTrustedEmptyDescription =>
      'Add networks you trust, like your home WiFi, to prevent auto-connecting when on these networks.';

  @override
  String get settingsTrustedNetworkSubtitle => 'Trusted network';

  @override
  String get settingsTrustedRemoveTooltip => 'Remove from trusted';

  @override
  String get settingsTrustedAddDialogTitle => 'Add Trusted Network';

  @override
  String get settingsTrustedSsidLabel => 'Network name (SSID)';

  @override
  String get settingsTrustedSsidHint => 'e.g. My Home WiFi';

  @override
  String get settingsTrustedAddButton => 'Add';

  @override
  String get settingsTrustedRemoveDialogTitle => 'Remove Network?';

  @override
  String settingsTrustedRemoveDialogContent(String ssid) {
    return 'Remove \"$ssid\" from trusted networks?';
  }

  @override
  String get settingsTrustedRemoveButton => 'Remove';

  @override
  String get settingsTrustedNotConnected =>
      'Not connected to WiFi or SSID unavailable';

  @override
  String settingsTrustedAddedNetwork(String ssid) {
    return 'Added \"$ssid\" to trusted networks';
  }

  @override
  String get settingsTrustedPermissionTitle => 'Permission Required';

  @override
  String get settingsTrustedPermissionPermanent =>
      'Location permission is required to detect WiFi networks. Please enable it in your device settings.';

  @override
  String get settingsTrustedPermissionRequired =>
      'Location permission is required to detect WiFi network names. This is a platform requirement for privacy reasons.';

  @override
  String get settingsTrustedOpenSettings => 'Open Settings';

  @override
  String get settingsTrustedTryAgain => 'Try Again';

  @override
  String get settingsAppearanceLoadError =>
      'Failed to load appearance settings';

  @override
  String get settingsBrightnessSection => 'Brightness';

  @override
  String get settingsTextSizeSection => 'Text Size';

  @override
  String get settingsDynamicColorLabel => 'Dynamic Color';

  @override
  String get settingsDynamicColorDescription =>
      'Use colors from your wallpaper';

  @override
  String get settingsOledModeLabel => 'OLED Dark Mode';

  @override
  String get settingsOledModeDescription =>
      'Use pure black backgrounds for maximum battery savings on OLED displays';

  @override
  String get settingsHighContrastLabel => 'High Contrast';

  @override
  String get settingsHighContrastDetected =>
      'High contrast mode is enabled at the system level. Colors are optimized for maximum readability.';

  @override
  String get settingsAnimationsSection => 'Animations';

  @override
  String get settingsReduceAnimations => 'Reduce Animations';

  @override
  String get settingsAnimationsDisabled => 'System animations are disabled';

  @override
  String get settingsAnimationsEnabled => 'System animations are enabled';

  @override
  String get settingsAnimationsSystemDisabled =>
      'Animations are disabled at the system level.';

  @override
  String get settingsThemeMaterialYou => 'Material You';

  @override
  String get settingsThemeCyberpunk => 'Cyberpunk';

  @override
  String get settingsTextScaleSystem => 'System';

  @override
  String get settingsTextScaleSmall => 'Small';

  @override
  String get settingsTextScaleDefault => 'Default';

  @override
  String get settingsTextScaleLarge => 'Large';

  @override
  String get settingsTextScaleExtraLarge => 'Extra Large';

  @override
  String get settingsTextScaleSystemDescription =>
      'Uses your device accessibility settings';

  @override
  String get settingsTextScaleSmallDescription =>
      'Smaller text for more content on screen';

  @override
  String get settingsTextScaleDefaultDescription => 'Default text size';

  @override
  String get settingsTextScaleLargeDescription =>
      'Larger text for improved readability';

  @override
  String get settingsTextScaleExtraLargeDescription =>
      'Maximum text size for accessibility';

  @override
  String get settingsTextSizePreview =>
      'Preview: The quick brown fox jumps over the lazy dog.';

  @override
  String get settingsNotificationLoadError =>
      'Failed to load notification settings';

  @override
  String get settingsNotificationGeneralSection => 'General';

  @override
  String get settingsNotificationExpiryLabel => 'Subscription expiry';

  @override
  String get settingsNotificationExpiryDescription =>
      'Reminders before your subscription expires';

  @override
  String get settingsNotificationPromotionalDescription =>
      'Offers, discounts, and new features';

  @override
  String get settingsNotificationReferralLabel => 'Referral activity';

  @override
  String get settingsNotificationReferralDescription =>
      'Updates on your referral rewards';

  @override
  String get settingsNotificationSecuritySection => 'Security';

  @override
  String get settingsNotificationSecurityRequired =>
      'Required for account security. Cannot be disabled.';

  @override
  String get settingsNotificationVpnSection => 'VPN Notification';

  @override
  String get settingsNotificationVpnSpeedLabel =>
      'Show speed in VPN notification';

  @override
  String get settingsNotificationVpnSpeedDescription =>
      'Display connection speed in persistent notification';

  @override
  String get settingsDeveloperExperimentalEnabled =>
      'Experimental features enabled';

  @override
  String get settingsDeveloperExperimentalDisabled =>
      'Experimental features disabled';

  @override
  String get configImportSubscriptionUrlTitle => 'Subscription URL Import';

  @override
  String get configImportPasteFailed => 'Failed to paste from clipboard';

  @override
  String configImportServersImported(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Imported $count servers',
      one: 'Imported 1 server',
    );
    return '$_temp0';
  }

  @override
  String get configImportSubscriptionFailed =>
      'Failed to import subscription URL';

  @override
  String get configImportSubscriptionUrlLabel => 'Subscription URL';

  @override
  String get configImportSubscriptionUrlHint => 'Enter subscription URL';

  @override
  String get configImportPasteTooltip => 'Paste from clipboard';

  @override
  String get configImportPleaseEnterUrl => 'Please enter a URL';

  @override
  String get configImportPleaseEnterValidUrl => 'Please enter a valid URL';

  @override
  String get configImportImporting => 'Importing...';

  @override
  String get configImportImportButton => 'Import';

  @override
  String get configImportNoSubscriptionUrls =>
      'No subscription URLs imported yet';

  @override
  String get configImportNoSubscriptionUrlsHint =>
      'Enter a subscription URL above to import servers';

  @override
  String get configImportDeleteSubscriptionTitle => 'Delete Subscription';

  @override
  String configImportDeleteSubscriptionContent(int count) {
    return 'Delete all $count servers from this subscription?';
  }

  @override
  String get configImportSubscriptionDeleted => 'Subscription deleted';

  @override
  String get configImportRefreshTooltip => 'Refresh subscription';

  @override
  String get configImportDeleteTooltip => 'Delete subscription';

  @override
  String get configImportSubscriptionRefreshed => 'Subscription refreshed';

  @override
  String configImportServerCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count servers',
      one: '1 server',
    );
    return '$_temp0';
  }

  @override
  String configImportLastUpdated(String timeAgo) {
    return 'Last updated: $timeAgo';
  }

  @override
  String get configImportTimeJustNow => 'Just now';

  @override
  String configImportTimeMinutesAgo(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count minutes ago',
      one: '1 minute ago',
    );
    return '$_temp0';
  }

  @override
  String configImportTimeHoursAgo(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count hours ago',
      one: '1 hour ago',
    );
    return '$_temp0';
  }

  @override
  String configImportTimeDaysAgo(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count days ago',
      one: '1 day ago',
    );
    return '$_temp0';
  }

  @override
  String get configImportDeleteServerTitle => 'Delete Server';

  @override
  String configImportRemoveServerContent(String name) {
    return 'Remove \"$name\" from your custom servers?';
  }

  @override
  String get configImportServerRemoved => 'Server removed';

  @override
  String get configImportRenameServerTitle => 'Rename Server';

  @override
  String get configImportServerNameLabel => 'Server name';

  @override
  String get configImportServerRenamed => 'Server renamed';

  @override
  String get configImportServerReachable => 'Server is reachable';

  @override
  String get configImportServerUnreachable => 'Server is unreachable';

  @override
  String get configImportExportQrTitle => 'Export as QR';

  @override
  String get configImportFromSubscriptionUrl => 'Import from Subscription URL';

  @override
  String get configImportNoServersAtUrl => 'No servers found at URL';

  @override
  String get configImportCustomServersTitle => 'Custom Servers';

  @override
  String get configImportClearAllButton => 'Clear All';

  @override
  String get configImportClearAllTitle => 'Clear All Servers';

  @override
  String get configImportClearAllContent =>
      'This will remove all custom servers. This action cannot be undone.';

  @override
  String get configImportAllServersRemoved => 'All custom servers removed';

  @override
  String get configImportNoCustomServers => 'No Custom Servers';

  @override
  String get configImportNoCustomServersHint =>
      'Import VPN configurations via QR code, clipboard, or subscription URL.';

  @override
  String get configImportImportServerButton => 'Import Server';

  @override
  String get configImportFailedToLoadServers => 'Failed to load servers';

  @override
  String get configImportSourceQrCode => 'QR Code';

  @override
  String get configImportSourceClipboard => 'Clipboard';

  @override
  String get configImportSourceSubscription => 'Subscription';

  @override
  String get configImportSourceDeepLink => 'Deep Link';

  @override
  String get configImportSourceManual => 'Manual';

  @override
  String get configImportTestConnection => 'Test Connection';

  @override
  String get configImportEditName => 'Edit Name';

  @override
  String get configImportNotTested => 'Not tested';

  @override
  String get configImportReachable => 'Reachable';

  @override
  String get configImportUnreachable => 'Unreachable';

  @override
  String get configImportTesting => 'Testing...';

  @override
  String configImportServerAdded(String name) {
    return 'Server added: $name';
  }

  @override
  String get configImportNoValidConfig => 'No valid VPN config in clipboard';

  @override
  String get configImportNoConfigInClipboard =>
      'No VPN configuration found in clipboard';

  @override
  String get configImportSwitchCamera => 'Switch camera';

  @override
  String get configImportNotValidConfig => 'Not a valid VPN configuration';

  @override
  String get configImportConfigFound => 'VPN Configuration Found';

  @override
  String get configImportNameLabel => 'Name';

  @override
  String get configImportUnknownServer => 'Unknown Server';

  @override
  String get configImportProtocolLabel => 'Protocol';

  @override
  String get configImportAddressLabel => 'Address';

  @override
  String get configImportAddServerButton => 'Add Server';

  @override
  String get configImportScanAnother => 'Scan Another';

  @override
  String get configImportPointCamera => 'Point your camera at a VPN QR code';

  @override
  String get configImportCameraPermissionRequired =>
      'Camera Permission Required';

  @override
  String get configImportCameraPermissionMessage =>
      'Please grant camera access in your device settings to scan QR codes.';

  @override
  String get configImportCameraError => 'Camera Error';

  @override
  String get configImportCameraStartFailed => 'Failed to start camera.';

  @override
  String get configImportFailedToAddServer => 'Failed to add server';

  @override
  String get configImportTransportLabel => 'Transport';

  @override
  String get configImportSecurityLabel => 'Security';

  @override
  String get configImportVpnConfigDetected => 'VPN Config Detected';

  @override
  String configImportFoundConfigs(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Found $count VPN configurations in your clipboard',
      one: 'Found 1 VPN configuration in your clipboard',
    );
    return '$_temp0';
  }

  @override
  String get configImportImportConfig => 'Import Config';

  @override
  String configImportImportAll(int count) {
    return 'Import All ($count)';
  }

  @override
  String get configImportDismiss => 'Dismiss';

  @override
  String get configImportDontAskAgain => 'Don\'t ask again';

  @override
  String configImportSuccessCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Successfully imported $count configs',
      one: 'Successfully imported 1 config',
    );
    return '$_temp0';
  }

  @override
  String configImportPartialSuccess(int success, int failure) {
    return 'Imported $success config(s), $failure failed';
  }

  @override
  String configImportFailureCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Failed to import $count configs',
      one: 'Failed to import config',
    );
    return '$_temp0';
  }

  @override
  String get subscriptionChooseYourPlan => 'Choose Your Plan';

  @override
  String get subscriptionDuration1Month => '1 Month';

  @override
  String get subscriptionDuration3Months => '3 Months';

  @override
  String get subscriptionDuration1Year => '1 Year';

  @override
  String get subscriptionCardView => 'Card View';

  @override
  String get subscriptionComparePlans => 'Compare Plans';

  @override
  String get subscriptionNoPlansForDuration =>
      'No plans available for this duration.';

  @override
  String get subscriptionFeatureLabel => 'Feature';

  @override
  String get subscriptionPriceLabel => 'Price';

  @override
  String get subscriptionTrafficLabel => 'Traffic';

  @override
  String get subscriptionDevicesLabel => 'Devices';

  @override
  String get subscriptionDurationLabel => 'Duration';

  @override
  String subscriptionTrafficGb(int count) {
    return '$count GB';
  }

  @override
  String get subscriptionUnlimited => 'Unlimited';

  @override
  String subscriptionDurationDays(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count days',
      one: '1 day',
    );
    return '$_temp0';
  }

  @override
  String get subscriptionCompletePurchase => 'Complete Purchase';

  @override
  String get subscriptionReviewYourOrder => 'Review Your Order';

  @override
  String get subscriptionContinueToPayment => 'Continue to Payment';

  @override
  String get subscriptionTotal => 'Total';

  @override
  String get subscriptionSelectPaymentMethod => 'Select Payment Method';

  @override
  String get subscriptionPayNow => 'Pay Now';

  @override
  String get subscriptionDoNotCloseApp => 'Please do not close the app.';

  @override
  String get subscriptionActivated => 'Subscription Activated!';

  @override
  String subscriptionActivatedMessage(String planName) {
    return 'You are now subscribed to $planName.';
  }

  @override
  String subscriptionSecureVpnAccess(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count days of secure VPN access',
      one: '1 day of secure VPN access',
    );
    return '$_temp0';
  }

  @override
  String get subscriptionStartUsingVpn => 'Start Using VPN';

  @override
  String get subscriptionPaymentFailed => 'Payment Failed';

  @override
  String get subscriptionTryAgain => 'Try Again';

  @override
  String get subscriptionPurchase => 'Purchase';

  @override
  String subscriptionPurchaseFlowFor(String planName) {
    return 'Purchase flow for: $planName';
  }

  @override
  String get subscriptionSelectPaymentMethodSnack =>
      'Please select a payment method';

  @override
  String get subscriptionPopular => 'Popular';

  @override
  String get subscriptionBestValue => 'Best Value';

  @override
  String get subscriptionFreeTrial => 'Free Trial';

  @override
  String subscriptionTrafficGbFeature(int count) {
    return '$count GB traffic';
  }

  @override
  String get subscriptionUnlimitedTraffic => 'Unlimited traffic';

  @override
  String subscriptionUpToDevices(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Up to $count devices',
      one: 'Up to 1 device',
    );
    return '$_temp0';
  }

  @override
  String get subscriptionPerMonth => '/ month';

  @override
  String get subscriptionPer3Months => '/ 3 months';

  @override
  String get subscriptionPerYear => '/ year';

  @override
  String get subscriptionPerLifetime => '/ lifetime';

  @override
  String get subscriptionStartFreeTrial => 'Start Free Trial';

  @override
  String get subscriptionDataUsage => 'Data Usage';

  @override
  String subscriptionPercentUsed(String percent) {
    return '$percent used';
  }

  @override
  String get subscriptionNoPaymentMethods => 'No payment methods available.';

  @override
  String get subscriptionApplePay => 'Apple Pay';

  @override
  String get subscriptionPayWithApplePay => 'Pay with Apple Pay';

  @override
  String get subscriptionGooglePay => 'Google Pay';

  @override
  String get subscriptionPayWithGooglePay => 'Pay with Google Pay';

  @override
  String get subscriptionCryptoBot => 'CryptoBot';

  @override
  String get subscriptionPayWithCrypto => 'Pay with Crypto';

  @override
  String get subscriptionYooKassa => 'YooKassa';

  @override
  String get subscriptionPayWithCard => 'Pay with Card (RU)';

  @override
  String get subscriptionQuarterly => 'Quarterly';

  @override
  String get serverTooltipFastest => 'Tap Fastest to auto-select best server';

  @override
  String get serverSortRecommended => 'Recommended';

  @override
  String get serverSortCountry => 'Country';

  @override
  String get serverSortLatency => 'Latency';

  @override
  String get serverSortLoad => 'Load';

  @override
  String get serverFastest => 'Fastest';

  @override
  String get serverRecentServers => 'Recent Servers';

  @override
  String get serverNoRecentServers =>
      'Connect to a server to see recent history';

  @override
  String get serverFailedToLoad => 'Failed to load servers';

  @override
  String get serverNotFound => 'Server not found';

  @override
  String get serverListClearSearch => '[EN] Clear search';

  @override
  String get serverSelectPrompt => '[EN] Select a server to view details';

  @override
  String get serverSingle => 'Server';

  @override
  String get serverDetailAddress => 'Address';

  @override
  String get serverDetailProtocol => 'Protocol';

  @override
  String get serverDetailStatus => 'Status';

  @override
  String get serverDetailOnline => 'Online';

  @override
  String get serverDetailOffline => 'Offline';

  @override
  String get serverDetailTier => 'Tier';

  @override
  String get serverDetailPremium => 'Premium';

  @override
  String get serverDetailLatency => 'Latency';

  @override
  String get serverDetailNotTested => 'Not tested';

  @override
  String get serverDetailServerLoad => 'Server Load';

  @override
  String get serverDetailUptime => 'Uptime';

  @override
  String get serverDetailUptimeValue => '99.9%';

  @override
  String get serverDetailUptimeNA => 'N/A';

  @override
  String get serverDetailUnavailable => 'Unavailable';

  @override
  String serverDetailConnectingTo(String name) {
    return 'Connecting to $name...';
  }

  @override
  String serverDetailFailedToConnect(String error) {
    return 'Failed to connect: $error';
  }

  @override
  String get serverCustomBadge => 'CUSTOM';

  @override
  String get serverFavoritesTitle => 'Favorites';

  @override
  String get serverNoFavoritesTitle => 'No favorites yet';

  @override
  String get serverNoFavoritesDescription =>
      'Tap the star icon on any server to add it here.';

  @override
  String get serverPingUnknown => '-- ms';

  @override
  String serverPingMs(int ping) {
    return '$ping ms';
  }

  @override
  String get a11ySelectFastestServer => 'Select fastest server';

  @override
  String get a11ySelectFastestServerHint =>
      'Tap to automatically connect to the fastest available server';

  @override
  String get a11yServerCardHint => 'Tap to view server details and connect';

  @override
  String get a11yToggleFavoriteHint => 'Tap to toggle favorite status';

  @override
  String get a11yMeasuringLatency => 'Measuring latency';

  @override
  String get a11yLatencyUnknown => 'Latency unknown';

  @override
  String a11yLatencyMs(int ping) {
    return 'Latency: $ping milliseconds';
  }

  @override
  String get a11yRetestLatencyHint => 'Tap to re-test server latency';

  @override
  String a11yServerInCity(String name, String city) {
    return '$name server in $city';
  }

  @override
  String get a11yStatusOnline => 'online';

  @override
  String get a11yStatusOffline => 'offline';

  @override
  String a11yLatencyMsShort(int ping) {
    return '$ping milliseconds latency';
  }

  @override
  String get a11yLatencyUnknownShort => 'latency unknown';

  @override
  String a11yLoadPercent(int load) {
    return '$load percent load';
  }

  @override
  String get a11yPremiumServer => 'premium server';

  @override
  String get a11yCustomServer => 'custom server';

  @override
  String get serverCustomCountry => 'Custom';

  @override
  String get referralTitle => 'Referrals';

  @override
  String get referralYourStats => 'Your Stats';

  @override
  String get referralRecentReferrals => 'Recent Referrals';

  @override
  String get referralActive => 'Active';

  @override
  String referralJoinedDate(String date) {
    return 'Joined $date';
  }

  @override
  String get referralNoReferralsYet => 'No referrals yet';

  @override
  String get referralShareCodePrompt =>
      'Share your code to start earning rewards!';

  @override
  String get referralComingSoonTitle => 'Referral Program Coming Soon';

  @override
  String get referralComingSoonDescription =>
      'Invite friends and earn rewards when they subscribe. Stay tuned for our upcoming referral program!';

  @override
  String get referralNotifyMeConfirmation =>
      'We\'ll notify you when referrals launch!';

  @override
  String get referralNotifyMe => 'Notify Me';

  @override
  String get referralCodeCopied => 'Referral code copied!';

  @override
  String referralShareMessage(String link) {
    return 'Join CyberVPN with my referral link: $link';
  }

  @override
  String get referralCopyCode => 'Copy code';

  @override
  String get referralQrCodeSemantics => 'Referral QR code';

  @override
  String get referralStatsTotalInvited => 'Total Invited';

  @override
  String get referralStatsPaidUsers => 'Paid Users';

  @override
  String get referralStatsPoints => 'Points';

  @override
  String get referralStatsBalance => 'Balance';

  @override
  String get diagnosticConnectionTitle => 'Connection Diagnostics';

  @override
  String get diagnosticSteps => 'Diagnostic Steps';

  @override
  String get diagnosticRunningTests => 'Running connection tests...';

  @override
  String get diagnosticCompleted => 'Diagnostics completed';

  @override
  String get diagnosticTapToStart => 'Tap Run Again to start';

  @override
  String get diagnosticUnknownStep => 'Unknown Step';

  @override
  String get diagnosticExportReport => 'Export Report';

  @override
  String get diagnosticRunning => 'Running...';

  @override
  String get diagnosticRunAgain => 'Run Again';

  @override
  String get diagnosticReportTitle => 'CyberVPN Connection Diagnostics Report';

  @override
  String diagnosticReportRanAt(String time) {
    return 'Ran at: $time';
  }

  @override
  String diagnosticReportTotalDuration(int seconds) {
    return 'Total duration: ${seconds}s';
  }

  @override
  String get diagnosticReportSteps => 'Steps:';

  @override
  String diagnosticReportStatus(String status) {
    return 'Status: $status';
  }

  @override
  String diagnosticReportDuration(String duration) {
    return 'Duration: $duration';
  }

  @override
  String get diagnosticReportDurationNa => 'N/A';

  @override
  String diagnosticReportMessage(String message) {
    return 'Message: $message';
  }

  @override
  String diagnosticReportSuggestion(String suggestion) {
    return 'Suggestion: $suggestion';
  }

  @override
  String get diagnosticStatusPending => 'PENDING';

  @override
  String get diagnosticStatusRunning => 'RUNNING';

  @override
  String get diagnosticStatusSuccess => 'SUCCESS';

  @override
  String get diagnosticStatusFailed => 'FAILED';

  @override
  String get diagnosticStatusWarning => 'WARNING';

  @override
  String get speedTestWithVpn => 'Test with VPN';

  @override
  String get speedTestNoResults => 'No speed tests yet';

  @override
  String get speedTestTapToStart => 'Tap Start to measure your connection';

  @override
  String get speedTestHistoryLabel => 'History';

  @override
  String get speedTestShareTitle => 'CyberVPN Speed Test Results';

  @override
  String speedTestShareDownload(String value) {
    return 'Download: $value Mbps';
  }

  @override
  String speedTestShareUpload(String value) {
    return 'Upload: $value Mbps';
  }

  @override
  String speedTestShareLatency(int value) {
    return 'Latency: $value ms';
  }

  @override
  String speedTestShareJitter(int value) {
    return 'Jitter: $value ms';
  }

  @override
  String get speedTestShareVpnOn => 'VPN: ON';

  @override
  String get speedTestShareVpnOff => 'VPN: OFF';

  @override
  String speedTestShareTestedAt(String time) {
    return 'Tested: $time';
  }

  @override
  String get speedTestVpnOn => 'VPN ON';

  @override
  String get speedTestVpnOff => 'VPN OFF';

  @override
  String get speedTestLatency => 'Latency';

  @override
  String get speedTestJitter => 'Jitter';

  @override
  String get speedTestCompare => 'Compare';

  @override
  String get speedTestHideCompare => 'Hide Compare';

  @override
  String get logViewerAutoScroll => 'Auto-scroll';

  @override
  String logViewerTotalEntries(int count) {
    return '$count total entries';
  }

  @override
  String logViewerFiltered(int count) {
    return '$count filtered';
  }

  @override
  String get logViewerSearchHint => 'Search logs...';

  @override
  String get logViewerNoLogsToExport => 'No logs to export';

  @override
  String get logViewerClearAllTitle => 'Clear All Logs?';

  @override
  String get logViewerClearCannotUndo => 'This action cannot be undone';

  @override
  String get logViewerClearedSuccess => 'Logs cleared successfully';

  @override
  String get logViewerNoLogsAvailable => 'No logs available';

  @override
  String get logViewerNoLogsMatchFilters => 'No logs match filters';

  @override
  String get logViewerFilterDebug => 'DEBUG';

  @override
  String get logViewerFilterInfo2 => 'INFO';

  @override
  String get logViewerFilterWarning2 => 'WARNING';

  @override
  String get logViewerFilterError2 => 'ERROR';

  @override
  String get connectionStatusNotProtected => 'Not Protected';

  @override
  String get connectionStatusProtected => 'Protected';

  @override
  String get connectionStatusReconnecting => 'Reconnecting...';

  @override
  String get connectionStatusConnectionError => 'Connection Error';

  @override
  String get connectionSelectServer => 'Select a server to connect';

  @override
  String get connectionPremium => 'Premium';

  @override
  String get connectionDuration => 'Duration';

  @override
  String get connectionMonitorSpeedTooltip =>
      'Monitor your real-time speed here';

  @override
  String get a11yConnectToVpn => 'Connect to VPN';

  @override
  String get a11yConnectingToVpn => 'Connecting to VPN';

  @override
  String get a11yDisconnectFromVpn => 'Disconnect from VPN';

  @override
  String get a11yDisconnectingFromVpn => 'Disconnecting from VPN';

  @override
  String get a11yReconnectingToVpn => 'Reconnecting to VPN';

  @override
  String get a11yRetryVpnConnection => 'Retry VPN connection';

  @override
  String get a11yTapToConnect => 'Tap to connect to the VPN server';

  @override
  String get a11yTapToDisconnect => 'Tap to disconnect from the VPN server';

  @override
  String get a11yTapToRetry => 'Tap to retry the connection';

  @override
  String get a11yPleaseWaitConnectionInProgress =>
      'Please wait, connection in progress';

  @override
  String get a11yPremiumSubscriptionActive => 'Premium subscription active';

  @override
  String a11yUsingProtocol(String protocol) {
    return 'Using $protocol protocol';
  }

  @override
  String a11yConnectionDurationValue(String duration) {
    return 'Connection duration: $duration';
  }

  @override
  String a11yIpAddress(String ip) {
    return 'IP address: $ip';
  }

  @override
  String a11yDownloadUploadSpeed(String download, String upload) {
    return 'Download speed: $download, Upload speed: $upload';
  }

  @override
  String a11yConnectedToServer(String name, String city, String country) {
    return 'Connected to $name server in $city, $country';
  }

  @override
  String get errorSomethingWentWrong => 'Something went wrong';

  @override
  String get errorUnexpectedDescription =>
      'An unexpected error occurred. You can report this issue or restart the app.';

  @override
  String errorFeatureCrashed(String feature) {
    return 'The $feature feature encountered an error.';
  }

  @override
  String get errorReport => 'Report';

  @override
  String get errorReported => 'Reported';

  @override
  String get errorRestart => 'Restart';

  @override
  String get offlineLabel => 'Offline';

  @override
  String get offlineYouAreOffline => 'You are offline';

  @override
  String get offlineSomeFeaturesUnavailable => 'Some features unavailable';

  @override
  String get offlineNotAvailable => 'Not available offline';

  @override
  String get offlineLastSyncJustNow => 'Last sync: just now';

  @override
  String offlineLastSyncMinutes(int count) {
    return 'Last sync: ${count}m ago';
  }

  @override
  String offlineLastSyncHours(int count) {
    return 'Last sync: ${count}h ago';
  }

  @override
  String offlineLastSyncDays(int count) {
    return 'Last sync: ${count}d ago';
  }

  @override
  String get updateRequired => 'Update Required';

  @override
  String get updateAvailable => 'Update Available';

  @override
  String get updateMandatoryDescription =>
      'A mandatory update is required to continue using CyberVPN.';

  @override
  String get updateOptionalDescription =>
      'A new version of CyberVPN is available with improvements and bug fixes.';

  @override
  String get updateCurrentVersion => 'Current Version:';

  @override
  String get updateLatestVersion => 'Latest Version:';

  @override
  String get updateRemindLater => 'Remind me in 3 days';

  @override
  String get updateNow => 'Update Now';

  @override
  String get updateLater => 'Later';

  @override
  String get splashTagline => 'Secure. Private. Fast.';

  @override
  String get navConnection => 'Connection';

  @override
  String autoConnectingToServer(String server) {
    return 'Auto-connecting to $server...';
  }

  @override
  String get autoConnectingToVpn => 'Auto-connecting to VPN...';

  @override
  String autoConnectFailed(String message) {
    return 'Auto-connect failed: $message';
  }

  @override
  String autoConnectSuccess(String server) {
    return 'Connected to $server';
  }

  @override
  String get dismiss => 'Dismiss';

  @override
  String get settingsScanlineLabel => 'Scanline Effect';

  @override
  String get settingsScanlineDescription =>
      'Subtle CRT scanline overlay for cyberpunk aesthetic';

  @override
  String get forceDisconnectTitle => 'Connection Terminated';

  @override
  String get forceDisconnectMessage =>
      'Your VPN connection was terminated by the server. This may be due to a session limit or administrative action.';

  @override
  String get serverQuickConnect => 'Connect';

  @override
  String get serverQuickFavorite => 'Add to Favorites';

  @override
  String get serverQuickUnfavorite => 'Remove from Favorites';

  @override
  String get serverQuickCopyAddress => 'Copy Address';

  @override
  String get serverQuickViewDetails => 'View Details';

  @override
  String get serverQuickReport => 'Report Issue';

  @override
  String get serverAddressCopied => 'Server address copied';

  @override
  String get serverReportSubmitted =>
      'Issue reported. Thank you for your feedback.';

  @override
  String get deleteAccountTitle => 'Delete Account';

  @override
  String get deleteAccountWarning =>
      'This action cannot be undone. All your data will be permanently deleted.';

  @override
  String get deleteAccountConsequence1 => 'Your subscription will be cancelled';

  @override
  String get deleteAccountConsequence2 =>
      'All VPN configurations will be removed';

  @override
  String get deleteAccountConsequence3 =>
      'Your account data will be permanently erased';

  @override
  String get deleteAccountConfirm => 'I understand, delete my account';

  @override
  String get deleteAccountReauthenticate =>
      'Please verify your identity to continue';

  @override
  String deleteAccountCountdown(int seconds) {
    return 'Delete Account (${seconds}s)';
  }

  @override
  String get deleteAccountFinalButton => 'Delete Account';

  @override
  String get deleteAccountSuccess => 'Your account has been deleted';

  @override
  String get deleteAccountPasswordLabel => 'Password';

  @override
  String get deleteAccountPasswordHint => 'Enter your password';

  @override
  String get deleteAccountOrBiometric => 'Or use biometric authentication';

  @override
  String get deleteAccountBiometricReason =>
      'Verify your identity to delete your account';
}
