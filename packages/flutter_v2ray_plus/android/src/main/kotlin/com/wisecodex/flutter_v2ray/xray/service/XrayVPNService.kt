package com.wisecodex.flutter_v2ray.xray.service

import android.content.Intent
import android.net.IpPrefix
import android.net.LocalSocket
import android.net.LocalSocketAddress
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import com.wisecodex.flutter_v2ray.xray.core.XrayCoreManager
import com.wisecodex.flutter_v2ray.xray.dto.XrayConfig
import com.wisecodex.flutter_v2ray.xray.utils.AppConfigs
import java.io.File
import java.net.Inet4Address
import java.net.Inet6Address
import java.net.InetAddress
import kotlin.math.max
import kotlin.math.min

/**
 * Android VPN Service implementation for XRay VPN.
 *
 * Responsibilities:
 * - Establishing the VPN interface (TUN device) using Android's VpnService API
 * - Managing the tun2socks process for traffic routing
 * - Handling VPN connection lifecycle (start, stop, cleanup)
 * - Supporting "Proxy Only" mode without VPN interface
 *
 * ## Technical Implementation
 * To support Android 15 (16KB page size) and prevent "bad file descriptor" errors,
 * the TUN file descriptor is passed to tun2socks via Unix Domain Socket instead of
 * command line arguments which fail across process boundaries.
 */
class XrayVPNService : VpnService() {

    // MARK: - Properties

    private var vpnInterface: ParcelFileDescriptor? = null
    private var tun2socksProcess: Process? = null
    private var isRunning = false

    // MARK: - Lifecycle Methods

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent ?: return START_NOT_STICKY.also { stopSelf() }

        val command = extractCommand(intent)
        when (command) {
            AppConfigs.V2RAY_SERVICE_COMMANDS.START_SERVICE -> {
                startForegroundService()
                handleStartCommand(intent)
            }
            AppConfigs.V2RAY_SERVICE_COMMANDS.STOP_SERVICE -> {
                stopAll()
                return START_NOT_STICKY
            }
            AppConfigs.V2RAY_SERVICE_COMMANDS.UPDATE_AUTO_DISCONNECT -> {
                val seconds = intent.getIntExtra("ADDITIONAL_SECONDS", 0)
                if (seconds > 0) {
                    XrayCoreManager.updateAutoDisconnectTime(this, seconds)
                }
                return START_STICKY
            }
            else -> {
                startForegroundService() // Ensure foreground for state sync if needed
                Log.w(TAG, "Unknown command received")
            }
        }

        return START_STICKY
    }

    override fun onDestroy() {
        stopAll()
        super.onDestroy()
    }

    // MARK: - Service Configuration

    private fun startForegroundService() {
        createNotificationChannel()
        val notification = createNotification("VPN Service Running")
        
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                // Android 14+ requires foreground service type
                startForeground(NOTIFICATION_ID, notification, FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
            Log.d(TAG, "Foreground service started successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start foreground service with primary method", e)
            // Fallback: try without service type for older behavior
            try {
                startForeground(NOTIFICATION_ID, notification)
                Log.d(TAG, "Foreground service started with fallback method")
            } catch (fallbackException: Exception) {
                Log.e(TAG, "Fallback foreground service also failed", fallbackException)
                // Last resort: stop the service to prevent ANR/crash
                stopSelf()
            }
        }
    }

    private fun extractCommand(intent: Intent): AppConfigs.V2RAY_SERVICE_COMMANDS? {
        return if (Build.VERSION.SDK_INT >= 33) {
            intent.getSerializableExtra("COMMAND", AppConfigs.V2RAY_SERVICE_COMMANDS::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getSerializableExtra("COMMAND") as? AppConfigs.V2RAY_SERVICE_COMMANDS
        }
    }

    @Synchronized
    private fun handleStartCommand(intent: Intent) {
        val config = extractConfig(intent) ?: return stopSelf()
        val proxyOnly = intent.getBooleanExtra("PROXY_ONLY", false)

        cleanup() // Ensure clean state

        if (XrayCoreManager.startCore(this, config)) {
            if (proxyOnly) {
                isRunning = true
                Log.d(TAG, "Started in PROXY_ONLY mode")
            } else {
                setupVpn(config)
            }
        } else {
            Log.e(TAG, "Failed to start XRay Core")
            stopSelf()
        }
    }

    private fun extractConfig(intent: Intent): XrayConfig? {
        return if (Build.VERSION.SDK_INT >= 33) {
            intent.getSerializableExtra("V2RAY_CONFIG", XrayConfig::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getSerializableExtra("V2RAY_CONFIG") as? XrayConfig
        }
    }

    // MARK: - VPN Setup

    /**
     * Establishes the VPN interface (TUN device) and starts tun2socks process.
     * Only after this succeeds do we notify XrayCoreManager to mark connection as active.
     */
    private fun setupVpn(config: XrayConfig) {
        try {
            // Check if VPN permission is still granted
            if (prepare(this) != null) {
                Log.e(TAG, "VPN permission not granted or was revoked")
                handleVpnEstablishmentFailure("VPN permission not granted")
                return
            }
            
            closeExistingInterface()
            
            // Build and establish VPN interface
            val builder = configureVpnBuilder(config)
            vpnInterface = builder.establish()

            // CRITICAL: Verify VPN interface was successfully established
            if (vpnInterface == null) {
                Log.e(TAG, "VPN interface establishment failed - builder.establish() returned null")
                Log.e(TAG, "This can happen if:")
                Log.e(TAG, "  1. Another VPN is currently active")
                Log.e(TAG, "  2. VPN permission was revoked")
                Log.e(TAG, "  3. Android system denied VPN due to resource constraints")
                handleVpnEstablishmentFailure("builder.establish() returned null")
                return
            }

            Log.d(TAG, "VPN interface established successfully")
            Log.d(TAG, "VPN file descriptor: ${vpnInterface?.fd}")
            
            // Mark local service state as running
            isRunning = true
            
            // Start tun2socks to route traffic
            runTun2socks(config)
            
            // CRITICAL: Only NOW tell XrayCoreManager that VPN is fully ready
            // This sets CONNECTED state, shows notification, and starts timer
            XrayCoreManager.onVpnEstablished(this)
            
        } catch (e: Exception) {
            Log.e(TAG, "Exception during VPN setup", e)
            stopAll()
        }
    }

    private fun closeExistingInterface() {
        vpnInterface?.runCatching {
            close()
            Thread.sleep(INTERFACE_CLOSE_DELAY_MS) // Allow system cleanup
        }?.onFailure {
            Log.e(TAG, "Error closing old VPN interface", it)
        }
        vpnInterface = null
    }

    private fun configureVpnBuilder(config: XrayConfig): Builder {
        return Builder().apply {
            setSession(config.REMARK)
            setMtu(resolveMtu(config))
            addAddress(VPN_ADDRESS, VPN_PREFIX_LENGTH)
            runCatching {
                addAddress(VPN_ADDRESS_V6, VPN_PREFIX_LENGTH_V6)
            }.onFailure {
                Log.w(TAG, "Failed to add IPv6 tunnel address", it)
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                setMetered(false)
            }

            // Exclude this app from VPN to prevent loops
            runCatching {
                addDisallowedApplication(packageName)
            }.onFailure {
                Log.e(TAG, "Failed to exclude app from VPN", it)
            }

            // Apply blocked apps (Per-App VPN)
            config.BLOCKED_APPS.forEach { blockedApp ->
                runCatching {
                    addDisallowedApplication(blockedApp)
                    Log.d(TAG, "Excluded app from VPN: $blockedApp")
                }.onFailure {
                    Log.w(TAG, "Failed to exclude app '$blockedApp' from VPN", it)
                }
            }

            configureRoutes(this, config)
            configureDns(this, config)
        }
    }

    private fun configureRoutes(builder: Builder, config: XrayConfig) {
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                builder.addRoute(DEFAULT_ROUTE_ADDRESS, DEFAULT_ROUTE_PREFIX)
                builder.addRoute(DEFAULT_ROUTE_ADDRESS_V6, DEFAULT_ROUTE_PREFIX_V6)
                configureExcludedRoutesApi33(builder, config)
                return@runCatching
            }

            val routes = buildIncludedRoutes(config)
            if (routes.isEmpty()) {
                builder.addRoute(DEFAULT_ROUTE_ADDRESS, DEFAULT_ROUTE_PREFIX)
                return@runCatching
            }

            routes.forEach { route ->
                val (address, prefix) = route.split("/")
                builder.addRoute(address, prefix.toInt())
            }
        }.onFailure {
            Log.e(TAG, "Failed to configure routes, using default route", it)
            builder.addRoute(DEFAULT_ROUTE_ADDRESS, DEFAULT_ROUTE_PREFIX)
        }
    }

    private fun configureExcludedRoutesApi33(builder: Builder, config: XrayConfig) {
        val excludedRoutes = mutableListOf<String>()

        val serverIp = config.CONNECTED_V2RAY_SERVER_ADDRESS
        when {
            isValidIpv4Address(serverIp) -> excludedRoutes.add("$serverIp/32")
            isValidIpv6Address(serverIp) -> excludedRoutes.add("$serverIp/128")
        }

        config.BYPASS_SUBNETS.forEach { route ->
            normalizeRoute(route)?.let(excludedRoutes::add) ?: run {
                Log.w(TAG, "Ignoring invalid bypass route: $route")
            }
        }

        excludedRoutes.distinct().forEach { route ->
            parseIpPrefix(route)?.let { prefix ->
                runCatching {
                    builder.excludeRoute(prefix)
                    Log.d(TAG, "Excluded route via IpPrefix API: $route")
                }.onFailure {
                    Log.w(TAG, "Failed to exclude route via IpPrefix API: $route", it)
                }
            }
        }
    }

    private fun configureDns(builder: Builder, config: XrayConfig) {
        val dnsServers = config.DNS_SERVERS ?: DEFAULT_DNS_SERVERS
        
        runCatching {
            dnsServers.forEach { builder.addDnsServer(it) }
        }.onFailure {
            Log.w(TAG, "Failed to configure DNS, using fallback", it)
            DEFAULT_DNS_FALLBACK.forEach { builder.addDnsServer(it) }
        }
    }

    private fun handleVpnEstablishmentFailure(reason: String = "Unknown") {
        Log.e(TAG, "========== VPN ESTABLISHMENT FAILED ==========")
        Log.e(TAG, "Reason: $reason")
        Log.e(TAG, "VPN interface will NOT be created")
        Log.e(TAG, "Cleaning up XrayCore and stopping service")
        Log.e(TAG, "=============================================")

        // Send DISCONNECTED broadcast to update app UI
        sendBroadcast(Intent(AppConfigs.V2RAY_CONNECTION_INFO).apply {
            putExtra("STATE", AppConfigs.V2RAY_STATES.V2RAY_DISCONNECTED)
        })

        // Stop XrayCore since VPN failed
        XrayCoreManager.stopCore(this)
        
        // Stop the service
        stopSelf()
    }

    // MARK: - Tun2socks Management

    /**
     * Starts the tun2socks process and initiates file descriptor transfer.
     */
    private fun runTun2socks(config: XrayConfig) {
        val tun2socksPath = File(applicationInfo.nativeLibraryDir, "libtun2socks.so").absolutePath
        val sockPath = File(filesDir, SOCKET_PATH).absolutePath

        val command = buildTun2socksCommand(tun2socksPath, sockPath, config)
        Log.d(TAG, "Starting tun2socks: ${command.joinToString(" ")}")

        runCatching {
            tun2socksProcess = ProcessBuilder(command).apply {
                redirectErrorStream(true)
                directory(filesDir)
            }.start()

            monitorTun2socksProcess(config)
            sendFd()
        }.onFailure {
            Log.e(TAG, "Failed to start tun2socks", it)
            stopAll()
        }
    }

    private fun buildTun2socksCommand(
        executablePath: String,
        socketPath: String,
        config: XrayConfig
    ): List<String> {
        return listOf(
            executablePath,
            "-sock-path", socketPath,
            "-proxy", "socks5://127.0.0.1:${config.LOCAL_SOCKS5_PORT}",
            "-mtu", resolveMtu(config).toString(),
            "-loglevel", TUN2SOCKS_LOG_LEVEL
        )
    }

    private fun monitorTun2socksProcess(config: XrayConfig) {
        Thread {
            runCatching {
                tun2socksProcess?.inputStream?.bufferedReader()?.use { reader ->
                    reader.forEachLine { line ->
                        Log.d(TAG, "tun2socks: $line")
                    }
                }

                val exitCode = tun2socksProcess?.waitFor()
                if (isRunning) {
                    Log.e(TAG, "tun2socks exited unexpectedly (code: $exitCode), restarting...")
                    Thread.sleep(TUN2SOCKS_START_DELAY_MS)
                    runTun2socks(config)
                }
            }.onFailure { exception ->
                when (exception) {
                    is java.io.InterruptedIOException, is InterruptedException -> {
                        // Expected when stopping
                        Log.d(TAG, "tun2socks monitor thread interrupted")
                    }
                    else -> Log.e(TAG, "Error in tun2socks monitor", exception)
                }
            }
        }.start()
    }

    // MARK: - File Descriptor Transfer

    /**
     * Sends the TUN interface file descriptor to the running tun2socks process.
     *
     * Uses a Unix Domain Socket to pass the FD across process boundaries,
     * which is required because ProcessBuilder cannot inherit FDs on Android.
     */
    private fun sendFd() {
        val fd = vpnInterface?.fileDescriptor ?: return
        val sockPath = File(filesDir, SOCKET_PATH).absolutePath

        Thread {
            repeat(FD_TRANSFER_MAX_RETRIES) { attempt ->
                runCatching {
                    Thread.sleep(FD_TRANSFER_RETRY_DELAY_MS)
                    
                    LocalSocket().use { socket ->
                        socket.connect(LocalSocketAddress(sockPath, LocalSocketAddress.Namespace.FILESYSTEM))
                        socket.setFileDescriptorsForSend(arrayOf(fd))
                        socket.outputStream.write(FD_TRANSFER_MAGIC_BYTE)
                        socket.setFileDescriptorsForSend(null)
                        socket.shutdownOutput()
                    }
                    
                    Log.d(TAG, "Successfully transferred TUN FD to tun2socks")
                    return@Thread
                }.onFailure {
                    if (attempt == FD_TRANSFER_MAX_RETRIES - 1) {
                        Log.e(TAG, "Failed to send FD after $FD_TRANSFER_MAX_RETRIES attempts", it)
                    }
                }
            }
        }.start()
    }

    // MARK: - Cleanup Methods

    /**
     * Cleans up VPN resources without stopping the service.
     * Used when restarting or switching configurations.
     */
    // MARK: - Cleanup
    private fun cleanup() {
        try {
            // Terminate tun2socks process
            tun2socksProcess?.let { process ->
                try {
                    process.destroy()
                    
                    // Wait up to 2 seconds for graceful termination
                    if (!process.waitFor(2, java.util.concurrent.TimeUnit.SECONDS)) {
                        Log.w(TAG, "tun2socks didn't terminate gracefully, forcing...")
                        process.destroyForcibly()
                        process.waitFor(1, java.util.concurrent.TimeUnit.SECONDS)
                    }
                    Log.d(TAG, "tun2socks process terminated")
                } catch (e: Exception) {
                    Log.e(TAG, "Error terminating tun2socks", e)
                }
            }
            tun2socksProcess = null

            // Close VPN interface
            closeExistingInterface()
        } catch (e: Exception) {
            Log.e(TAG, "Error during cleanup", e)
        } finally {
            isRunning = false
        }
    }

    /**
     * Stops all components: tun2socks, VPN interface, and XRay Core.
     */
    private fun stopAll() {
        cleanup()
        XrayCoreManager.stopCore(this)
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        
        stopSelf()
    }

    private fun buildIncludedRoutes(config: XrayConfig): List<String> {
        var routes = mutableListOf(DEFAULT_ROUTE)
        val excludedCidrs = mutableListOf<String>()

        val serverIp = config.CONNECTED_V2RAY_SERVER_ADDRESS
        if (isValidIpv4Address(serverIp)) {
            val serverCidr = "$serverIp/32"
            Log.d(TAG, "Excluding server IP from VPN routes: $serverCidr")
            excludedCidrs.add(serverCidr)
        } else if (serverIp.isNotBlank()) {
            Log.w(
                TAG,
                "Legacy route subtraction ignores non-IPv4 server address on API < 33: $serverIp",
            )
        }

        config.BYPASS_SUBNETS.forEach { route ->
            val normalized = normalizeRoute(route)
            if (normalized != null && isValidIpv4Cidr(normalized)) {
                excludedCidrs.add(normalized)
            } else if (normalized != null && normalized.contains(':')) {
                Log.w(
                    TAG,
                    "Legacy route subtraction ignores IPv6 route on API < 33: $normalized",
                )
            } else {
                Log.w(TAG, "Ignoring invalid bypass subnet: $route")
            }
        }

        excludedCidrs.forEach { excludedCidr ->
            val nextRoutes = subtractCidrRoutes(routes, excludedCidr)
            if (nextRoutes.isEmpty()) {
                Log.w(
                    TAG,
                    "Ignoring excluded route $excludedCidr because it removes all VPN routes",
                )
                return@forEach
            }
            routes = nextRoutes.toMutableList()
        }

        return routes
    }

    private fun subtractCidrRoutes(routes: List<String>, excludedCidr: String): List<String> {
        val excludedRange = cidrToRange(excludedCidr) ?: return routes
        val updatedRoutes = mutableListOf<String>()

        routes.forEach { route ->
            val routeRange = cidrToRange(route)
            if (routeRange == null) {
                updatedRoutes.add(route)
                return@forEach
            }

            subtractRange(routeRange, excludedRange).forEach { range ->
                updatedRoutes.addAll(rangeToCidrs(range.start, range.end))
            }
        }

        return updatedRoutes.distinct()
    }

    private fun subtractRange(source: IpRange, excluded: IpRange): List<IpRange> {
        if (excluded.end < source.start || excluded.start > source.end) {
            return listOf(source)
        }

        val result = mutableListOf<IpRange>()
        val overlapStart = max(source.start, excluded.start)
        val overlapEnd = min(source.end, excluded.end)

        if (source.start < overlapStart) {
            result.add(IpRange(source.start, overlapStart - 1))
        }
        if (overlapEnd < source.end) {
            result.add(IpRange(overlapEnd + 1, source.end))
        }

        return result
    }

    private fun rangeToCidrs(start: Long, end: Long): List<String> {
        val cidrs = mutableListOf<String>()
        var current = start

        while (current <= end) {
            var blockSize = if (current == 0L) {
                1L shl 32
            } else {
                current and -current
            }

            val remaining = end - current + 1
            while (blockSize > remaining) {
                blockSize = blockSize shr 1
            }

            val prefix = 32 - java.lang.Long.numberOfTrailingZeros(blockSize)
            cidrs.add("${longToIp(current)}/$prefix")
            current += blockSize
        }

        return cidrs
    }

    private fun cidrToRange(cidr: String): IpRange? {
        val parts = cidr.split("/")
        if (parts.size != 2) {
            return null
        }

        val prefix = parts[1].toIntOrNull()?.takeIf { it in 0..32 } ?: return null
        val address = ipv4ToLong(parts[0]) ?: return null
        val mask = if (prefix == 0) {
            0L
        } else {
            (0xFFFFFFFFL shl (32 - prefix)) and 0xFFFFFFFFL
        }
        val network = address and mask
        val broadcast = network or (0xFFFFFFFFL xor mask)
        return IpRange(network, broadcast)
    }

    private fun ipv4ToLong(ip: String): Long? {
        val parts = ip.split(".")
        if (parts.size != 4) {
            return null
        }

        var value = 0L
        for (part in parts) {
            val octet = part.toIntOrNull()?.takeIf { it in 0..255 } ?: return null
            value = (value shl 8) + octet
        }
        return value
    }

    private fun isValidIpv4Address(ip: String): Boolean {
        return ipv4ToLong(ip) != null
    }

    private fun isValidIpv6Address(ip: String): Boolean {
        return runCatching {
            InetAddress.getByName(ip) is Inet6Address
        }.getOrDefault(false)
    }

    private fun isValidIpv4Cidr(cidr: String): Boolean {
        return cidrToRange(cidr) != null
    }

    private fun normalizeRoute(route: String): String? {
        val trimmed = route.trim()
        if (trimmed.isEmpty()) {
            return null
        }
        if (trimmed.contains("/")) {
            return trimmed
        }
        return when {
            isValidIpv4Address(trimmed) -> "$trimmed/32"
            isValidIpv6Address(trimmed) -> "$trimmed/128"
            else -> null
        }
    }

    private fun parseIpPrefix(route: String): IpPrefix? {
        val normalized = normalizeRoute(route) ?: return null
        val parts = normalized.split("/")
        if (parts.size != 2) {
            return null
        }

        return runCatching {
            val address = InetAddress.getByName(parts[0])
            val prefix = parts[1].toInt()
            when (address) {
                is Inet4Address -> if (prefix in 0..32) IpPrefix(address, prefix) else null
                is Inet6Address -> if (prefix in 0..128) IpPrefix(address, prefix) else null
                else -> null
            }
        }.getOrNull()
    }

    private fun resolveMtu(config: XrayConfig): Int {
        return config.MTU?.takeIf { it > 0 } ?: VPN_MTU
    }

    private fun longToIp(ip: Long): String {
        return "${(ip shr 24) and 0xFF}.${(ip shr 16) and 0xFF}.${(ip shr 8) and 0xFF}.${ip and 0xFF}"
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channelId = "vpn_service_channel"
            val channelName = "VPN Service"
            val channel = android.app.NotificationChannel(
                channelId,
                channelName,
                android.app.NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(android.app.NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun createNotification(content: String): android.app.Notification {
        val channelId = "vpn_service_channel"
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            android.app.Notification.Builder(this, channelId)
        } else {
            @Suppress("DEPRECATION")
            android.app.Notification.Builder(this)
        }
        
        // Use a default icon if not set
        val icon = android.R.drawable.ic_dialog_info
        
        builder
            .setContentTitle("VPN Service")
            .setContentText(content)
            .setSmallIcon(icon)
            .setOngoing(true)
        
        // Android 12+ (API 31): Show notification immediately instead of 10-second delay
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setForegroundServiceBehavior(android.app.Notification.FOREGROUND_SERVICE_IMMEDIATE)
        }
        
        return builder.build()
    }

    // MARK: - Companion Object

    companion object {
        private const val TAG = "XrayVPNService"
        
        // Notification
        private const val NOTIFICATION_ID = 1
        private const val FOREGROUND_SERVICE_TYPE_SPECIAL_USE = 32
        
        // VPN Configuration
        private const val VPN_MTU = 1500
        private const val VPN_ADDRESS = "26.26.26.1"
        private const val VPN_PREFIX_LENGTH = 30
        private const val VPN_ADDRESS_V6 = "fd66:26:26::1"
        private const val VPN_PREFIX_LENGTH_V6 = 126
        private const val DEFAULT_ROUTE_ADDRESS = "0.0.0.0"
        private const val DEFAULT_ROUTE_PREFIX = 0
        private const val DEFAULT_ROUTE = "$DEFAULT_ROUTE_ADDRESS/$DEFAULT_ROUTE_PREFIX"
        private const val DEFAULT_ROUTE_ADDRESS_V6 = "::"
        private const val DEFAULT_ROUTE_PREFIX_V6 = 0
        
        // DNS Configuration
        private val DEFAULT_DNS_SERVERS = arrayListOf("8.8.8.8", "114.114.114.114")
        private val DEFAULT_DNS_FALLBACK = arrayListOf("8.8.8.8", "1.1.1.1")
        
        // Tun2socks Configuration
        private const val SOCKET_PATH = "sock_path"
        private const val TUN2SOCKS_MTU = 1500
        private const val TUN2SOCKS_LOG_LEVEL = "debug"
        
        // File Descriptor Transfer
        private const val FD_TRANSFER_MAX_RETRIES = 10
        private const val FD_TRANSFER_RETRY_DELAY_MS = 500L
        private const val FD_TRANSFER_MAGIC_BYTE = 32
        
        // Timing
        private const val INTERFACE_CLOSE_DELAY_MS = 200L
        private const val TUN2SOCKS_START_DELAY_MS = 1000L
    }
}

private data class IpRange(
    val start: Long,
    val end: Long,
)
