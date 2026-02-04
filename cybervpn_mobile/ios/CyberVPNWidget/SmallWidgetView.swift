import SwiftUI
import WidgetKit

struct SmallWidgetView: View {
    let entry: VPNStatusEntry

    var body: some View {
        ZStack {
            // Cyberpunk dark background gradient
            LinearGradient(
                colors: [
                    Color(hex: "0A0E1A"), // Dark blue-black
                    Color(hex: "1A1F35")  // Slightly lighter blue
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            // Content
            VStack(spacing: 8) {
                // Status icon
                Image(systemName: entry.status.iconName)
                    .font(.system(size: 32, weight: .bold))
                    .foregroundColor(entry.status.color)
                    .shadow(color: entry.status.color.opacity(0.5), radius: 4)

                // Status text
                Text(entry.status.displayText)
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundColor(entry.status.color)
                    .textCase(.uppercase)
                    .shadow(color: entry.status.color.opacity(0.3), radius: 2)
            }
            .padding()
        }
        .widgetURL(URL(string: "cybervpn://widget-action"))
    }
}

// MARK: - Preview
struct SmallWidgetView_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            SmallWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "US East",
                uploadSpeed: "1.2 MB/s",
                downloadSpeed: "5.8 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Connected")

            SmallWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .disconnected,
                serverName: "Not connected",
                uploadSpeed: "0 KB/s",
                downloadSpeed: "0 KB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Disconnected")

            SmallWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connecting,
                serverName: "Germany",
                uploadSpeed: "0 KB/s",
                downloadSpeed: "0 KB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemSmall))
            .previewDisplayName("Connecting")
        }
    }
}
