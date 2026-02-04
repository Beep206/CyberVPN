import SwiftUI
import WidgetKit

struct MediumWidgetView: View {
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

            HStack(spacing: 16) {
                // Left: Status icon and text
                VStack(spacing: 6) {
                    Image(systemName: entry.status.iconName)
                        .font(.system(size: 40, weight: .bold))
                        .foregroundColor(entry.status.color)
                        .shadow(color: entry.status.color.opacity(0.5), radius: 4)

                    Text(entry.status.displayText)
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundColor(entry.status.color)
                        .textCase(.uppercase)
                        .shadow(color: entry.status.color.opacity(0.3), radius: 2)
                }
                .frame(width: 80)

                // Right: Server info and connection speeds
                VStack(alignment: .leading, spacing: 8) {
                    // Server name with icon
                    HStack(spacing: 6) {
                        Image(systemName: "server.rack")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "00ffff"))

                        Text(entry.serverName)
                            .font(.system(size: 13, weight: .semibold, design: .monospaced))
                            .foregroundColor(.white)
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                    }

                    // Divider
                    Rectangle()
                        .fill(Color(hex: "00ff88").opacity(0.3))
                        .frame(height: 1)

                    // Upload speed
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "00ff88"))

                        Text(entry.uploadSpeed)
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundColor(Color(hex: "00ff88"))
                    }

                    // Download speed
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.down.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "00ffff"))

                        Text(entry.downloadSpeed)
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundColor(Color(hex: "00ffff"))
                    }
                }
                .padding(.trailing, 8)

                Spacer(minLength: 0)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .widgetURL(URL(string: "cybervpn://widget-action"))
    }
}

// MARK: - Preview
struct MediumWidgetView_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "US East",
                uploadSpeed: "1.2 MB/s",
                downloadSpeed: "5.8 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Connected")

            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .disconnected,
                serverName: "Not connected",
                uploadSpeed: "0 KB/s",
                downloadSpeed: "0 KB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Disconnected")

            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connecting,
                serverName: "Germany Frankfurt",
                uploadSpeed: "0 KB/s",
                downloadSpeed: "0 KB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Connecting")

            MediumWidgetView(entry: VPNStatusEntry(
                date: Date(),
                status: .connected,
                serverName: "Singapore Central Region with Very Long Name",
                uploadSpeed: "15.3 MB/s",
                downloadSpeed: "42.7 MB/s"
            ))
            .previewContext(WidgetPreviewContext(family: .systemMedium))
            .previewDisplayName("Long Name + High Speed")
        }
    }
}
