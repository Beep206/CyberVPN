import WidgetKit
import SwiftUI

/// Entry model for VPN status widget
struct VPNStatusEntry: TimelineEntry {
    let date: Date
    let status: VPNStatus
    let serverName: String
    let uploadSpeed: String
    let downloadSpeed: String

    /// VPN connection status
    enum VPNStatus: String {
        case connected
        case disconnected
        case connecting

        /// Display text for status
        var displayText: String {
            switch self {
            case .connected:
                return "CONNECTED"
            case .disconnected:
                return "DISCONNECTED"
            case .connecting:
                return "CONNECTING"
            }
        }

        /// SF Symbol icon name for status
        var iconName: String {
            switch self {
            case .connected:
                return "checkmark.shield.fill"
            case .disconnected:
                return "xmark.shield.fill"
            case .connecting:
                return "arrow.clockwise.circle.fill"
            }
        }

        /// Color for status (cyberpunk theme)
        var color: Color {
            switch self {
            case .connected:
                return Color(hex: "00ff88") // Matrix green
            case .disconnected:
                return Color(hex: "ff00ff") // Neon pink
            case .connecting:
                return Color(hex: "00ffff") // Neon cyan
            }
        }
    }
}

// MARK: - Color Extension
extension Color {
    /// Initialize Color from hex string
    /// - Parameter hex: Hex color string without # prefix (e.g., "00ff88")
    init(hex: String) {
        let scanner = Scanner(string: hex)
        var rgbValue: UInt64 = 0
        scanner.scanHexInt64(&rgbValue)

        let r = Double((rgbValue & 0xFF0000) >> 16) / 255.0
        let g = Double((rgbValue & 0x00FF00) >> 8) / 255.0
        let b = Double(rgbValue & 0x0000FF) / 255.0

        self.init(red: r, green: g, blue: b)
    }
}
