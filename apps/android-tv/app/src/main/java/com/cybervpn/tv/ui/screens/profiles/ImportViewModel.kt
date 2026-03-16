package com.cybervpn.tv.ui.screens.profiles

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.net.NetworkInterface
import javax.inject.Inject

@Suppress(
    "NestedBlockDepth",
    "TooGenericExceptionCaught",
    "SwallowedException",
    "MagicNumber"
)
@HiltViewModel
class ImportViewModel @Inject constructor() : ViewModel() {

    private val _ipAddress = MutableStateFlow<String?>(null)
    val ipAddress: StateFlow<String?> = _ipAddress.asStateFlow()

    private val _pairingCode = MutableStateFlow<String?>(null)
    val pairingCode: StateFlow<String?> = _pairingCode.asStateFlow()

    init {
        fetchLocalIp()
        generatePairingCode()
    }

    private fun fetchLocalIp() {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                val addresses = networkInterface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val inetAddress = addresses.nextElement()
                    if (!inetAddress.isLoopbackAddress && inetAddress.address.size == 4) {
                        _ipAddress.value = inetAddress.hostAddress
                        return
                    }
                }
            }
        } catch (e: Exception) {
            _ipAddress.value = "Unknown IP"
        }
    }

    private fun generatePairingCode() {
        val charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        val code = (1..6).map { charset.random() }.joinToString("")
        val formatted = "${code.take(3)}-${code.takeLast(3)}"
        _pairingCode.value = formatted
    }
}
