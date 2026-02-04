import WidgetKit
import SwiftUI

struct VPNStatusProvider: TimelineProvider {
    /// App Group identifier for shared UserDefaults
    /// Must match the App Group configured in Xcode for both main app and widget
    private let appGroupId = "group.com.cybervpn.widgets"

    // UserDefaults keys - must match Flutter side
    private let keyVpnStatus = "vpn_status"
    private let keyServerName = "server_name"
    private let keyUploadSpeed = "upload_speed"
    private let keyDownloadSpeed = "download_speed"
    private let keyLastUpdate = "last_update"

    // MARK: - TimelineProvider Protocol

    /// Placeholder shown in widget gallery before user adds widget
    func placeholder(in context: Context) -> VPNStatusEntry {
        VPNStatusEntry(
            date: Date(),
            status: .disconnected,
            serverName: "Select Server",
            uploadSpeed: "0 KB/s",
            downloadSpeed: "0 KB/s"
        )
    }

    /// Snapshot for transient display (e.g., widget gallery preview)
    func getSnapshot(in context: Context, completion: @escaping (VPNStatusEntry) -> Void) {
        let entry = loadCurrentStatus()
        completion(entry)
    }

    /// Timeline for widget updates
    /// iOS will request new timelines as needed based on the policy
    func getTimeline(in context: Context, completion: @escaping (Timeline<VPNStatusEntry>) -> Void) {
        let currentEntry = loadCurrentStatus()

        // Create timeline with single entry
        // Widget will refresh after 15 minutes
        let refreshDate = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!

        // Use .after policy to request a new timeline after the refresh date
        let timeline = Timeline(entries: [currentEntry], policy: .after(refreshDate))

        completion(timeline)
    }

    // MARK: - Data Loading

    /// Load current VPN status from shared UserDefaults
    private func loadCurrentStatus() -> VPNStatusEntry {
        // Access shared UserDefaults via App Group
        guard let userDefaults = UserDefaults(suiteName: appGroupId) else {
            // If App Group is not accessible, return placeholder
            // This can happen if App Group is not properly configured in Xcode
            return placeholder(in: Context())
        }

        // Read values with defaults
        let statusString = userDefaults.string(forKey: keyVpnStatus) ?? "disconnected"
        let status = VPNStatusEntry.VPNStatus(rawValue: statusString) ?? .disconnected
        let serverName = userDefaults.string(forKey: keyServerName) ?? "Not connected"
        let uploadSpeed = userDefaults.string(forKey: keyUploadSpeed) ?? "0 KB/s"
        let downloadSpeed = userDefaults.string(forKey: keyDownloadSpeed) ?? "0 KB/s"

        return VPNStatusEntry(
            date: Date(),
            status: status,
            serverName: serverName,
            uploadSpeed: uploadSpeed,
            downloadSpeed: downloadSpeed
        )
    }
}

// MARK: - Context Extension
extension Context {
    /// Helper to create default context for placeholder
    init() {
        // This is a workaround since Context doesn't have a public initializer
        // In real usage, Context is always provided by WidgetKit
        self.init(family: .systemSmall, isPreview: false)
    }
}
