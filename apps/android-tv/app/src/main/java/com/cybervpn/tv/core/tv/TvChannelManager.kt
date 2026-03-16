@file:Suppress("FunctionNaming", "MagicNumber", "TooGenericExceptionCaught", "SwallowedException")

package com.cybervpn.tv.core.tv

import android.annotation.SuppressLint
import android.content.ContentUris
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.tvprovider.media.tv.Channel
import androidx.tvprovider.media.tv.PreviewProgram
import androidx.tvprovider.media.tv.TvContractCompat
import com.cybervpn.tv.service.CyberVpnService
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TvChannelManager @Inject constructor(
    @ApplicationContext private val context: Context
) {

    @SuppressLint("RestrictedApi")
    fun initializePlayNext() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val cursor =
                    context.contentResolver.query(
                        TvContractCompat.Channels.CONTENT_URI,
                        arrayOf(TvContractCompat.Channels._ID),
                        null,
                        null,
                        null
                    )

                var channelId: Long = -1
                if (cursor != null && cursor.moveToFirst()) {
                    channelId = cursor.getLong(0)
                }
                cursor?.close()

                if (channelId == -1L) {
                    val builder =
                        Channel.Builder()
                            .setDisplayName("CyberVPN Quick Connect")
                            .setType(TvContractCompat.Channels.TYPE_PREVIEW)
                            .setAppLinkIntentUri(Uri.parse("cybervpn://quick_connect"))

                    val uri =
                        context.contentResolver.insert(
                            TvContractCompat.Channels.CONTENT_URI,
                            builder.build().toContentValues()
                        )
                    if (uri != null) {
                        channelId = ContentUris.parseId(uri)
                        TvContractCompat.requestChannelBrowsable(context, channelId)
                    }
                }

                if (channelId != -1L) {
                    val intent =
                        Intent(context, CyberVpnService::class.java).apply {
                            action = "com.cybervpn.tv.ACTION_CONNECT"
                        }
                    val intentUri = Uri.parse(intent.toUri(Intent.URI_INTENT_SCHEME))

                    val programBuilder =
                        PreviewProgram.Builder()
                            .setChannelId(channelId)
                            .setTitle("Tap to Connect")
                            .setDescription("Instantly secure your network")
                            .setIntentUri(intentUri)
                            .setWeight(100)

                    context.contentResolver.insert(
                        TvContractCompat.PreviewPrograms.CONTENT_URI,
                        programBuilder.build().toContentValues()
                    )
                }
            } catch (e: Exception) {
                // Ignore exceptions if provider is unavailable
            }
        }
    }
}
