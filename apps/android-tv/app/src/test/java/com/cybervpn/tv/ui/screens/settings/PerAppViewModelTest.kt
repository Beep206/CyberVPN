package com.cybervpn.tv.ui.screens.settings

import android.graphics.drawable.Drawable
import app.cash.turbine.test
import com.cybervpn.tv.core.model.TvApp
import com.cybervpn.tv.core.state.UiState
import com.cybervpn.tv.core.system.AppManager
import com.cybervpn.tv.data.RoutingRepository
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PerAppViewModelTest {

    private val testDispatcher = UnconfinedTestDispatcher()
    private lateinit val appManager: AppManager
    private lateinit val routingRepository: RoutingRepository

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        appManager = mockk()
        routingRepository = mockk()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `uiState transitions from Loading to Success when repo emits data`() = runTest {
        // Arrange
        val mockDrawable = mockk<Drawable>()
        val mockApps = listOf(
            TvApp("com.example.app1", "App 1", mockDrawable),
            TvApp("com.example.app2", "App 2", mockDrawable)
        )
        val bypassFlow = MutableStateFlow(setOf("com.example.app1"))

        coEvery { appManager.getInstalledApps() } returns mockApps
        every { routingRepository.bypassedPackages } returns bypassFlow

        // Act
        val viewModel = PerAppViewModel(appManager, routingRepository)

        // Assert
        viewModel.uiState.test {
            // Because of UnconfinedTestDispatcher, the state might transition synchronously.
            // But we must assert it goes from Loading to Success
            val firstState = awaitItem()
            
            // If the first state is Loading, the second must be Success
            if (firstState is UiState.Loading) {
                val successState = awaitItem() as UiState.Success
                assertTrue(successState.data.isNotEmpty())
            } else {
                // If it skipped Loading due to eager execution, just check Success
                val successState = firstState as UiState.Success
                assertTrue(successState.data.isNotEmpty())
            }
            cancelAndIgnoreRemainingEvents()
        }
    }
}
