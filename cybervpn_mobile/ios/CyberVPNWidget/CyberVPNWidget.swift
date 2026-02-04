import WidgetKit
import SwiftUI

@main
struct CyberVPNWidgetBundle: WidgetBundle {
    var body: some Widget {
        SmallVPNWidget()
        MediumVPNWidget()
    }
}

struct SmallVPNWidget: Widget {
    let kind: String = "SmallVPNWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: VPNStatusProvider()) { entry in
            SmallWidgetView(entry: entry)
        }
        .configurationDisplayName("VPN Status")
        .description("Shows your current VPN connection status")
        .supportedFamilies([.systemSmall])
    }
}

struct MediumVPNWidget: Widget {
    let kind: String = "MediumVPNWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: VPNStatusProvider()) { entry in
            MediumWidgetView(entry: entry)
        }
        .configurationDisplayName("VPN Details")
        .description("Shows VPN status, server, and connection speeds")
        .supportedFamilies([.systemMedium])
    }
}

// MARK: - Preview Provider
struct CyberVPNWidget_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            // Small widget preview - connected state
            SmallWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "US East",
                uploadSpeed: "1.2 MB/s",
                downloadSpeed: "5.8 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Small - Connected")

            // Small widget preview - disconnected state
            SmallWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .disconnected,
                serverName: "Not connected",
                uploadSpeed: "0 KB/s",
                downloadSpeed: "0 KB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Small - Disconnected")

            // Medium widget preview - connected state
            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "US East",
                uploadSpeed: "1.2 MB/s",
                downloadSpeed: "5.8 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Medium - Connected")

            // Medium widget preview - connecting state
            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connecting,
                serverName: "Germany Frankfurt",
                uploadSpeed: "0 KB/s",
                downloadSpeed: "0 KB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Medium - Connecting")
        }
    }
}
