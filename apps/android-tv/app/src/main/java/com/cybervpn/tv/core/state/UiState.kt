package com.cybervpn.tv.core.state

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>

    data class Success<out T>(val data: T) : UiState<T>

    data class Error(val message: String, val cause: Throwable? = null) : UiState<Nothing>
}
