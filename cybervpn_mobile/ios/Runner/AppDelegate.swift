import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
  private var secureTextField: UITextField?

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)

    // Set up screen protection channel
    if let controller = window?.rootViewController as? FlutterViewController {
      let channel = FlutterMethodChannel(
        name: "com.cybervpn.cybervpn_mobile/screen_protection",
        binaryMessenger: controller.binaryMessenger
      )

      channel.setMethodCallHandler { [weak self] (call: FlutterMethodCall, result: @escaping FlutterResult) in
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

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  /// Enables screenshot protection using the secure text field overlay technique
  private func enableScreenProtection() {
    guard secureTextField == nil else { return }
    guard let window = self.window else { return }

    // Create a transparent, secure text field that covers the entire screen
    let textField = UITextField(frame: window.bounds)
    textField.isSecureTextEntry = true
    textField.isUserInteractionEnabled = false
    textField.backgroundColor = .clear
    textField.alpha = 0.0

    // Add it to the window but keep it hidden
    window.addSubview(textField)
    window.sendSubviewToBack(textField)

    // Make it the first responder to activate secure mode
    textField.becomeFirstResponder()
    textField.resignFirstResponder()

    secureTextField = textField
  }

  /// Disables screenshot protection by removing the secure text field overlay
  private func disableScreenProtection() {
    secureTextField?.removeFromSuperview()
    secureTextField = nil
  }
}
