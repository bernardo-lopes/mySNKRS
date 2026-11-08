package app.mysnkrs.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * The same palette as the web app's _theme.html. "fg" is the strong foreground (headings,
 * primary button), "ink" are the backgrounds from page (900) to borders (500).
 */
@Immutable
data class SnkrsColors(
    val isLight: Boolean,
    val fg: Color,
    val fgInverse: Color,
    val gray100: Color,
    val gray200: Color,
    val gray300: Color,
    val gray400: Color,
    val gray500: Color,
    val ink900: Color,
    val ink800: Color,
    val ink700: Color,
    val ink600: Color,
    val ink500: Color,
    val positive: Color,
    val negative: Color,
    val warning: Color,
    val up: Color = Color(0xFF3FA36B),
    val star: Color = Color(0xFFF5B301),
)

val DarkPalette = SnkrsColors(
    isLight = false,
    fg = Color(0xFFFFFFFF), fgInverse = Color(0xFF000000),
    gray100 = Color(0xFFF3F4F6), gray200 = Color(0xFFE5E7EB), gray300 = Color(0xFFD1D5DB),
    gray400 = Color(0xFF9CA3AF), gray500 = Color(0xFF6B7280),
    ink900 = Color(0xFF0B0C10), ink800 = Color(0xFF15171E), ink700 = Color(0xFF1E212A),
    ink600 = Color(0xFF2A2E3A), ink500 = Color(0xFF3A3F4D),
    positive = Color(0xFF6EE7B7), negative = Color(0xFFFDA4AF), warning = Color(0xFFFCD34D),
)

val LightPalette = SnkrsColors(
    isLight = true,
    fg = Color(0xFF111318), fgInverse = Color(0xFFFFFFFF),
    gray100 = Color(0xFF1F2329), gray200 = Color(0xFF2B2F36), gray300 = Color(0xFF3D424B),
    gray400 = Color(0xFF5F6672), gray500 = Color(0xFF7C838F),
    ink900 = Color(0xFFF6F7F9), ink800 = Color(0xFFFFFFFF), ink700 = Color(0xFFEEF0F3),
    ink600 = Color(0xFFE2E5EA), ink500 = Color(0xFFC9CED6),
    positive = Color(0xFF047857), negative = Color(0xFFBE123C), warning = Color(0xFFB45309),
)

val LocalSnkrsColors = staticCompositionLocalOf { DarkPalette }

object Snkrs {
    val colors: SnkrsColors @Composable get() = LocalSnkrsColors.current
}

@Composable
fun SnkrsTheme(light: Boolean, content: @Composable () -> Unit) {
    val c = if (light) LightPalette else DarkPalette
    val base = if (light) lightColorScheme() else darkColorScheme()
    val scheme = base.copy(
        primary = c.fg, onPrimary = c.fgInverse,
        secondary = c.gray300, onSecondary = c.fgInverse,
        background = c.ink900, onBackground = c.gray200,
        surface = c.ink800, onSurface = c.gray200,
        surfaceVariant = c.ink700, onSurfaceVariant = c.gray400,
        surfaceContainer = c.ink800, surfaceContainerHigh = c.ink800, surfaceContainerHighest = c.ink700,
        surfaceContainerLow = c.ink800, surfaceContainerLowest = c.ink900,
        outline = c.ink600, outlineVariant = c.ink700,
        error = c.negative, onError = c.fgInverse,
        secondaryContainer = c.ink700, onSecondaryContainer = c.fg,
    )
    CompositionLocalProvider(LocalSnkrsColors provides c) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}
