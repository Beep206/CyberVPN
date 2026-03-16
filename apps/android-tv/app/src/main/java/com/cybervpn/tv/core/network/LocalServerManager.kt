package com.cybervpn.tv.core.network

import com.cybervpn.tv.core.parser.VpnParser
import com.cybervpn.tv.data.db.VpnDao
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.serialization.kotlinx.json.json
import io.ktor.server.application.call
import io.ktor.server.application.install
import io.ktor.server.cio.CIO
import io.ktor.server.engine.embeddedServer
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.plugins.cors.routing.CORS
import io.ktor.server.request.receiveText
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.routing
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Suppress("LongMethod", "MaxLineLength", "MagicNumber")
@Singleton
class LocalServerManager @Inject constructor(
    private val vpnDao: VpnDao
) {
    private val scope = CoroutineScope(Dispatchers.IO)
    private var server: io.ktor.server.engine.ApplicationEngine? = null

    fun startServer() {
        if (server != null) return

        scope.launch {
            server =
                embeddedServer(CIO, port = 8080) {
                    install(CORS) {
                        anyHost()
                    }
                    install(ContentNegotiation) {
                        json()
                    }
                    routing {
                        get("/") {
                            val html =
                                """
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <meta name="viewport" content="width=device-width, initial-scale=1">
                                    <title>CyberVPN Import</title>
                                    <style>
                                        body { background: #0a0a0a; color: #00ff88; font-family: monospace; display: flex; flex-direction: column; align-items: center; padding: 2rem; }
                                        input { background: #111; color: #fff; border: 1px solid #00ff88; padding: 1rem; width: 100%; max-width: 400px; margin-bottom: 1rem; }
                                        button { background: #00ff88; color: #000; border: none; padding: 1rem 2rem; font-weight: bold; cursor: pointer; }
                                    </style>
                                </head>
                                <body>
                                    <h2>Import VPN Configuration</h2>
                                    <input type="text" id="vpnUrl" placeholder="vless://... or vmess://..." />
                                    <button onclick="sendUrl()">SEND TO TV</button>
                                    <p id="status"></p>
                                    <script>
                                        async function sendUrl() {
                                            const url = document.getElementById('vpnUrl').value;
                                            if(!url) return;
                                            try {
                                                const res = await fetch('/api/import', { method: 'POST', body: url });
                                                document.getElementById('status').innerText = res.ok ? 'SUCCESS' : 'FAILED: ' + await res.text();
                                            } catch(e) {
                                                document.getElementById('status').innerText = 'NETWORK ERROR';
                                            }
                                        }
                                    </script>
                                </body>
                                </html>
                                """.trimIndent()
                            call.respondText(html, ContentType.Text.Html)
                        }

                        post("/api/import") {
                            val payload = call.receiveText()
                            val nodes = VpnParser.parse(payload)
                            if (nodes.isEmpty()) {
                                call.respondText("Invalid Link or Parsing Failed", status = HttpStatusCode.BadRequest)
                            } else {
                                vpnDao.insertNodes(nodes)
                                call.respondText("Successfully imported ${nodes.size} nodes", status = HttpStatusCode.OK)
                            }
                        }
                    }
                }
            server?.start(wait = false)
        }
    }

    fun stopServer() {
        server?.stop(gracePeriodMillis = 1000, timeoutMillis = 2000)
        server = null
    }
}
