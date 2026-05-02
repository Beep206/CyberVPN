import AuthenticationServices
import CryptoKit
import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
  private let screenProtectionChannelName = "com.cybervpn.cybervpn_mobile/screen_protection"
  private let telegramNativeAuthChannelName =
    "com.cybervpn.cybervpn_mobile/telegram_native_auth"

  private var secureTextField: UITextField?
  private var telegramNativeAuthResult: FlutterResult?
  private var telegramNativeRedirectURL: URL?

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)

    if let controller = window?.rootViewController as? FlutterViewController {
      setUpScreenProtectionChannel(binaryMessenger: controller.binaryMessenger)
      setUpTelegramNativeAuthChannel(binaryMessenger: controller.binaryMessenger)
    }

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  override func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey: Any] = [:]
  ) -> Bool {
    if handleTelegramNativeAuthCallback(url) {
      return true
    }

    return super.application(app, open: url, options: options)
  }

  override func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
  ) -> Bool {
    if userActivity.activityType == NSUserActivityTypeBrowsingWeb,
      let url = userActivity.webpageURL,
      handleTelegramNativeAuthCallback(url)
    {
      return true
    }

    return super.application(
      application,
      continue: userActivity,
      restorationHandler: restorationHandler
    )
  }

  private func setUpScreenProtectionChannel(binaryMessenger: FlutterBinaryMessenger) {
    let channel = FlutterMethodChannel(
      name: screenProtectionChannelName,
      binaryMessenger: binaryMessenger
    )

    channel.setMethodCallHandler { [weak self] call, result in
      switch call.method {
      case "enableProtection":
        self?.enableScreenProtection()
        result(true)
      case "disableProtection":
        self?.disableScreenProtection()
        result(true)
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  private func setUpTelegramNativeAuthChannel(binaryMessenger: FlutterBinaryMessenger) {
    let channel = FlutterMethodChannel(
      name: telegramNativeAuthChannelName,
      binaryMessenger: binaryMessenger
    )

    channel.setMethodCallHandler { [weak self] call, result in
      guard let self else {
        result(
          FlutterError(
            code: "UNAVAILABLE",
            message: "Telegram native auth handler is unavailable.",
            details: nil
          )
        )
        return
      }

      switch call.method {
      case "login":
        self.startTelegramNativeLogin(call: call, result: result)
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  private func startTelegramNativeLogin(call: FlutterMethodCall, result: @escaping FlutterResult) {
    guard telegramNativeAuthResult == nil else {
      result(
        FlutterError(
          code: "IN_PROGRESS",
          message: "Telegram native login is already in progress.",
          details: nil
        )
      )
      return
    }

    guard let arguments = call.arguments as? [String: Any] else {
      result(
        FlutterError(
          code: "INVALID_ARGUMENTS",
          message: "Telegram native login expects a configuration payload.",
          details: nil
        )
      )
      return
    }

    let clientId =
      (arguments["clientId"] as? String)?
      .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    let redirectUri =
      (arguments["redirectUri"] as? String)?
      .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    let requestedScopes =
      (arguments["scopes"] as? [String])?
      .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } ?? []

    guard !clientId.isEmpty, !redirectUri.isEmpty, let redirectURL = URL(string: redirectUri) else {
      result(
        FlutterError(
          code: "NOT_CONFIGURED",
          message: "Telegram native login is not configured for this build.",
          details: nil
        )
      )
      return
    }

    let scopes = requestedScopes.isEmpty ? ["profile"] : requestedScopes

    telegramNativeAuthResult = result
    telegramNativeRedirectURL = redirectURL

    let fallbackScheme: String?
    if redirectURL.scheme?.lowercased() == "https" {
      fallbackScheme = "cybervpn"
    } else {
      fallbackScheme = redirectURL.scheme
    }

    Task { @MainActor in
      TelegramLogin.configure(
        clientId: clientId,
        redirectUri: redirectUri,
        scopes: scopes,
        fallbackScheme: fallbackScheme
      )

      TelegramLogin.login { [weak self] loginResult in
        DispatchQueue.main.async {
          self?.completeTelegramNativeLogin(loginResult)
        }
      }
    }
  }

  private func handleTelegramNativeAuthCallback(_ url: URL) -> Bool {
    guard isTelegramNativeAuthCallback(url) else {
      return false
    }

    Task { @MainActor in
      TelegramLogin.handle(url) { [weak self] loginResult in
        DispatchQueue.main.async {
          self?.completeTelegramNativeLogin(loginResult)
        }
      }
    }

    return true
  }

  private func isTelegramNativeAuthCallback(_ url: URL) -> Bool {
    guard let expectedURL = telegramNativeRedirectURL else {
      return false
    }

    let expectedScheme = expectedURL.scheme?.lowercased()
    let expectedHost = expectedURL.host?.lowercased()
    let expectedPath = normalizedCallbackPath(expectedURL.path)
    let incomingScheme = url.scheme?.lowercased()
    let incomingHost = url.host?.lowercased()
    let incomingPath = normalizedCallbackPath(url.path)

    guard incomingScheme == expectedScheme else {
      return false
    }

    if let expectedHost, !expectedHost.isEmpty, incomingHost != expectedHost {
      return false
    }

    if expectedPath != "/" {
      return incomingPath == expectedPath || incomingPath.hasPrefix(expectedPath + "/")
    }

    return true
  }

  private func normalizedCallbackPath(_ path: String) -> String {
    let trimmed = path.trimmingCharacters(in: .whitespacesAndNewlines)
    return trimmed.isEmpty ? "/" : trimmed
  }

  private func completeTelegramNativeLogin(_ loginResult: Result<LoginData, Error>) {
    guard let flutterResult = telegramNativeAuthResult else {
      return
    }

    telegramNativeAuthResult = nil
    telegramNativeRedirectURL = nil

    switch loginResult {
    case .success(let loginData):
      flutterResult([
        "idToken": loginData.idToken
      ])
    case .failure(let error):
      flutterResult(mapTelegramNativeAuthError(error))
    }
  }

  private func mapTelegramNativeAuthError(_ error: Error) -> FlutterError {
    guard let telegramError = error as? TelegramLoginError else {
      return FlutterError(
        code: "LOGIN_FAILED",
        message: error.localizedDescription,
        details: nil
      )
    }

    switch telegramError {
    case .cancelled:
      return FlutterError(
        code: "CANCELLED",
        message: telegramError.localizedDescription,
        details: nil
      )
    case .notConfigured:
      return FlutterError(
        code: "NOT_CONFIGURED",
        message: telegramError.localizedDescription,
        details: nil
      )
    case .serverError(let statusCode):
      return FlutterError(
        code: "SERVER_ERROR",
        message: telegramError.localizedDescription,
        details: [
          "statusCode": statusCode
        ]
      )
    case .noAuthorizationCode, .requestFailed:
      return FlutterError(
        code: "LOGIN_FAILED",
        message: telegramError.localizedDescription,
        details: nil
      )
    }
  }

  /// Enables screenshot protection using the secure text field overlay technique.
  private func enableScreenProtection() {
    guard secureTextField == nil else { return }
    guard let window = self.window else { return }

    let textField = UITextField(frame: window.bounds)
    textField.isSecureTextEntry = true
    textField.isUserInteractionEnabled = false
    textField.backgroundColor = .clear
    textField.alpha = 0.0

    window.addSubview(textField)
    window.sendSubviewToBack(textField)

    textField.becomeFirstResponder()
    textField.resignFirstResponder()

    secureTextField = textField
  }

  /// Disables screenshot protection by removing the secure text field overlay.
  private func disableScreenProtection() {
    secureTextField?.removeFromSuperview()
    secureTextField = nil
  }
}

// Vendored from the official Telegram iOS Login SDK with minimal local
// adaptation for the Flutter Runner target:
// https://github.com/TelegramMessenger/telegram-login-ios

public struct LoginData: Sendable {
  public let idToken: String

  public init(idToken: String) {
    self.idToken = idToken
  }
}

public enum TelegramLoginError: Error, LocalizedError, Sendable, Equatable {
  case notConfigured
  case noAuthorizationCode
  case serverError(statusCode: Int)
  case requestFailed(String)
  case cancelled

  public var errorDescription: String? {
    switch self {
    case .notConfigured:
      return "TelegramLogin is not configured. Call TelegramLogin.configure() first."
    case .noAuthorizationCode:
      return "No authorization code found in callback URL."
    case .serverError(let code):
      return "Server returned HTTP \(code)."
    case .requestFailed(let message):
      return message
    case .cancelled:
      return "Login was cancelled."
    }
  }
}

public enum TelegramLogin {
  private struct Configuration: Sendable {
    let clientId: String
    let redirectUri: String
    let scopes: [String]
    let fallbackScheme: String?
  }

  private static var configuration: Configuration?
  private static var pendingCompletion: (@Sendable (Result<LoginData, Error>) -> Void)?
  private static var authSession: ASWebAuthenticationSession?
  private static var codeVerifier: String?
  private static let baseURL = "https://oauth.telegram.org"

  @MainActor
  public static func configure(
    clientId: String,
    redirectUri: String,
    scopes: [String],
    fallbackScheme: String? = nil
  ) {
    configuration = Configuration(
      clientId: clientId,
      redirectUri: redirectUri,
      scopes: scopes,
      fallbackScheme: fallbackScheme
    )
  }

  @MainActor
  public static func login(
    completion: @escaping @Sendable (Result<LoginData, Error>) -> Void
  ) {
    guard let configuration else {
      completion(.failure(TelegramLoginError.notConfigured))
      return
    }

    pendingCompletion = completion
    codeVerifier = generateCodeVerifier()

    Task {
      await performLogin(configuration: configuration, completion: completion)
    }
  }

  @MainActor
  public static func handle(
    _ url: URL,
    completion: (@Sendable (Result<LoginData, Error>) -> Void)? = nil
  ) {
    let callback = completion ?? pendingCompletion
    pendingCompletion = nil

    guard let callback else { return }
    guard let configuration else {
      callback(.failure(TelegramLoginError.notConfigured))
      return
    }

    guard let code = URLComponents(url: url, resolvingAgainstBaseURL: false)?
      .queryItems?
      .first(where: { $0.name == "code" })?
      .value
    else {
      callback(.failure(TelegramLoginError.noAuthorizationCode))
      return
    }

    Task {
      do {
        let token = try await exchangeCode(code, configuration: configuration)
        callback(.success(LoginData(idToken: token)))
      } catch {
        callback(.failure(error))
      }
    }
  }

  @MainActor
  private static func performLogin(
    configuration: Configuration,
    completion: @escaping @Sendable (Result<LoginData, Error>) -> Void
  ) async {
    if let tgCheck = URL(string: "tg://resolve"),
      UIApplication.shared.canOpenURL(tgCheck)
    {
      if let crossAppURL = try? await fetchCrossAppURL(configuration: configuration),
        UIApplication.shared.canOpenURL(crossAppURL)
      {
        await UIApplication.shared.open(crossAppURL)
        return
      }
    }

    startWebAuthSession(configuration: configuration, completion: completion)
  }

  @MainActor
  private static func startWebAuthSession(
    configuration: Configuration,
    completion: @escaping @Sendable (Result<LoginData, Error>) -> Void
  ) {
    guard let authURL = buildAuthURL(configuration: configuration) else {
      completion(.failure(TelegramLoginError.requestFailed("Could not build auth URL.")))
      return
    }

    let handleResult: (URL?, Error?) -> Void = { callbackURL, error in
      authSession = nil

      if let error {
        if (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin {
          completion(.failure(TelegramLoginError.cancelled))
        } else {
          completion(.failure(error))
        }
        return
      }

      guard let callbackURL else {
        completion(.failure(TelegramLoginError.noAuthorizationCode))
        return
      }

      Task { @MainActor in
        handle(callbackURL, completion: completion)
      }
    }

    let session: ASWebAuthenticationSession

    if #available(iOS 17.4, *),
      let components = URLComponents(string: configuration.redirectUri),
      components.scheme?.lowercased() == "https",
      let host = components.host
    {
      let path = components.path.isEmpty ? "/" : components.path
      let callback = ASWebAuthenticationSession.Callback.https(host: host, path: path)
      session = ASWebAuthenticationSession(url: authURL, callback: callback) {
        callbackURL,
          error in
        handleResult(callbackURL, error)
      }
    } else {
      let callbackScheme =
        configuration.fallbackScheme ??
        URLComponents(string: configuration.redirectUri)?.scheme

      session = ASWebAuthenticationSession(
        url: authURL,
        callbackURLScheme: callbackScheme
      ) { callbackURL, error in
        handleResult(callbackURL, error)
      }
    }

    session.presentationContextProvider = PresentationContextProvider.shared
    session.prefersEphemeralWebBrowserSession = false

    authSession = session
    session.start()
  }

  private static func fetchCrossAppURL(configuration: Configuration) async throws -> URL? {
    guard var components = URLComponents(string: "\(baseURL)/crossapp") else {
      return nil
    }

    var queryItems = [
      URLQueryItem(name: "client_id", value: configuration.clientId),
      URLQueryItem(name: "response_type", value: "code"),
      URLQueryItem(name: "redirect_uri", value: configuration.redirectUri),
      URLQueryItem(name: "scope", value: configuration.scopes.joined(separator: " ")),
      URLQueryItem(name: "ios_sdk", value: "1"),
    ]

    if let verifier = codeVerifier {
      queryItems.append(URLQueryItem(name: "code_challenge", value: codeChallenge(for: verifier)))
      queryItems.append(URLQueryItem(name: "code_challenge_method", value: "S256"))
    }

    components.queryItems = queryItems

    guard let url = components.url else { return nil }

    let (data, response) = try await URLSession.shared.data(from: url)
    guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
      return nil
    }

    struct CrossAppResponse: Decodable {
      let url: String?
    }

    return try JSONDecoder()
      .decode(CrossAppResponse.self, from: data)
      .url
      .flatMap(URL.init(string:))
  }

  private static func buildAuthURL(configuration: Configuration) -> URL? {
    guard var components = URLComponents(string: "\(baseURL)/auth") else {
      return nil
    }

    var queryItems = [
      URLQueryItem(name: "client_id", value: configuration.clientId),
      URLQueryItem(name: "response_type", value: "code"),
      URLQueryItem(name: "redirect_uri", value: configuration.redirectUri),
      URLQueryItem(name: "scope", value: configuration.scopes.joined(separator: " ")),
      URLQueryItem(name: "ios_sdk", value: "1"),
    ]

    if let verifier = codeVerifier {
      queryItems.append(URLQueryItem(name: "code_challenge", value: codeChallenge(for: verifier)))
      queryItems.append(URLQueryItem(name: "code_challenge_method", value: "S256"))
    }

    components.queryItems = queryItems
    return components.url
  }

  private static func exchangeCode(
    _ code: String,
    configuration: Configuration
  ) async throws -> String {
    guard let url = URL(string: "\(baseURL)/token") else {
      throw TelegramLoginError.requestFailed("Invalid token endpoint URL.")
    }

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue(
      "application/x-www-form-urlencoded",
      forHTTPHeaderField: "Content-Type"
    )

    var bodyItems = [
      URLQueryItem(name: "client_id", value: configuration.clientId),
      URLQueryItem(name: "code", value: code),
      URLQueryItem(name: "grant_type", value: "authorization_code"),
      URLQueryItem(name: "redirect_uri", value: configuration.redirectUri),
    ]

    if let verifier = codeVerifier {
      bodyItems.append(URLQueryItem(name: "code_verifier", value: verifier))
      codeVerifier = nil
    }

    var body = URLComponents()
    body.queryItems = bodyItems
    request.httpBody = body.query?.data(using: .utf8)

    let (data, response) = try await URLSession.shared.data(for: request)
    guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
      let statusCode = (response as? HTTPURLResponse)?.statusCode ?? -1
      throw TelegramLoginError.serverError(statusCode: statusCode)
    }

    struct TokenResponse: Decodable {
      let id_token: String?
      let error: String?
    }

    let parsed = try JSONDecoder().decode(TokenResponse.self, from: data)
    if let token = parsed.id_token {
      return token
    }

    throw TelegramLoginError.requestFailed(parsed.error ?? "Unexpected token response.")
  }
}

private func generateCodeVerifier() -> String {
  var bytes = [UInt8](repeating: 0, count: 32)
  _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)

  return Data(bytes)
    .base64EncodedString()
    .replacingOccurrences(of: "+", with: "-")
    .replacingOccurrences(of: "/", with: "_")
    .replacingOccurrences(of: "=", with: "")
}

private func codeChallenge(for verifier: String) -> String {
  let digest = SHA256.hash(data: Data(verifier.utf8))
  return Data(digest)
    .base64EncodedString()
    .replacingOccurrences(of: "+", with: "-")
    .replacingOccurrences(of: "/", with: "_")
    .replacingOccurrences(of: "=", with: "")
}

private final class PresentationContextProvider: NSObject,
  ASWebAuthenticationPresentationContextProviding
{
  static let shared = PresentationContextProvider()

  func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
    UIApplication.shared.connectedScenes
      .compactMap { $0 as? UIWindowScene }
      .flatMap { $0.windows }
      .first(where: \.isKeyWindow) ?? ASPresentationAnchor()
  }
}
