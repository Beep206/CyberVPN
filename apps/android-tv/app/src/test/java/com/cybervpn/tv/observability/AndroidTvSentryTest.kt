package com.cybervpn.tv.observability

import io.sentry.SentryEvent
import io.sentry.protocol.Request
import io.sentry.protocol.User
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidTvSentryTest {
    @Test
    fun `resolve falls back to canonical defaults`() {
        val contract =
            AndroidTvSentry.resolve(
                dsn = "",
                environment = "",
                release = "",
                versionName = "1.2.3",
                versionCode = 42,
            )

        assertEquals("", contract.dsn)
        assertEquals("development", contract.environment)
        assertEquals("android-tv@1.2.3+42", contract.release)
        assertEquals("42", contract.dist)
        assertFalse(contract.enabled)
    }

    @Test
    fun `build config contract exposes release and environment`() {
        val contract = AndroidTvSentry.fromBuildConfig()

        assertTrue(contract.environment.isNotBlank())
        assertTrue(contract.release.startsWith("android-tv@"))
        assertEquals(contract.dist, com.cybervpn.tv.BuildConfig.VERSION_CODE.toString())
    }

    @Test
    fun `sanitize event strips user and request`() {
        val event = SentryEvent()
        event.setUser(User().apply { id = "internal-user-id" })
        event.setRequest(Request())

        val sanitized = AndroidTvSentry.sanitizeEvent(event)

        assertNull(sanitized.user)
        assertNull(sanitized.request)
    }

    @Test
    fun `resolve keeps explicit runtime values`() {
        val contract =
            AndroidTvSentry.resolve(
                dsn = "https://android-tv@example.com/7",
                environment = "production",
                release = "android-tv@9.9.9+123",
                versionName = "9.9.9",
                versionCode = 123,
            )

        assertEquals("https://android-tv@example.com/7", contract.dsn)
        assertEquals("production", contract.environment)
        assertEquals("android-tv@9.9.9+123", contract.release)
        assertEquals("123", contract.dist)
        assertTrue(contract.enabled)
        assertNotNull(contract.release)
    }
}
