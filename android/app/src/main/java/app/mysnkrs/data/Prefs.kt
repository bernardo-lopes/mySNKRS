package app.mysnkrs.data

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

enum class ThemeMode { SYSTEM, LIGHT, DARK }

/** Settings kept on the phone: server address, theme and the favorites filter. */
class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("mysnkrs", Context.MODE_PRIVATE)

    var serverUrl by mutableStateOf(sp.getString("server_url", "") ?: "")
        private set
    var themeMode by mutableStateOf(
        runCatching { ThemeMode.valueOf(sp.getString("theme", "SYSTEM")!!) }.getOrDefault(ThemeMode.SYSTEM)
    )
        private set
    var favoritesOnly by mutableStateOf(sp.getBoolean("favorites_only", false))
        private set

    fun updateServerUrl(v: String) {
        serverUrl = v.trim()
        sp.edit().putString("server_url", serverUrl).apply()
    }

    fun updateThemeMode(v: ThemeMode) {
        themeMode = v
        sp.edit().putString("theme", v.name).apply()
    }

    fun updateFavoritesOnly(v: Boolean) {
        favoritesOnly = v
        sp.edit().putBoolean("favorites_only", v).apply()
    }
}
