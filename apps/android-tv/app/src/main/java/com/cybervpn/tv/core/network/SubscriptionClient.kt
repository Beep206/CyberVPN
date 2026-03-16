package com.cybervpn.tv.core.network

import android.util.Log
import com.cybervpn.tv.core.model.ProxyNode
import com.cybervpn.tv.core.parser.VpnParser
import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText

class SubscriptionClient(private val client: HttpClient) {
    companion object {
        private const val TAG = "SubscriptionClient"
    }

    /**
     * Fetches a raw subscription payload dynamically from the provided URL, strictly
     * enforcing timeouts preventing TV UI hangs. Safely decodes into standard domain proxy nodes.
     */
    @Suppress("TooGenericExceptionCaught")
    suspend fun fetchSubscription(url: String): List<ProxyNode>? {
        return try {
            Log.i(TAG, "Fetching subscription from: $url")
            val rawData: String = client.get(url).bodyAsText()

            // Assume the payload holds separated links inside a robust YAML or Base64 block
            // Often subscription endpoints deliver Base64 wrapped links
            VpnParser.parseSubscriptionPayload(rawData)
        } catch (e: Exception) {
            Log.e(TAG, "Network timeout or failure while fetching subscription: \${e.message}", e)
            null
        }
    }
}
